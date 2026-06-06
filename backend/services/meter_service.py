"""
电表记录 Service。
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException, UploadFile
import os, shutil, uuid

from database import UPLOAD_DIR, validate_upload, safe_write_upload
from models.orm import MeterReading, Contract, MoveInInspection, Bill, BillOtherFee, PaymentAllocation
from services.helpers import get_or_404, next_code, check_status
from services.constants import ELECTRICITY_RATE


def _recalculate_bill_total(db: Session, bill: Bill) -> None:
    """重新计算账单总额和状态（公共函数，避免 create/update 重复代码）"""
    bill.total = round(bill.rent + bill.water_fee + bill.electricity_fee, 2)
    # 加上其他费用
    other_total = db.scalar(
        select(func.coalesce(func.sum(BillOtherFee.amount), 0))
        .where(BillOtherFee.bill_id == bill.id)
    ) or 0
    bill.total = round(bill.total + other_total, 2)
    # 重算账单状态：根据已付金额判断
    paid = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .where(PaymentAllocation.bill_id == bill.id)
    ) or 0
    if paid >= bill.total:
        bill.status = "已付"
    elif paid > 0:
        bill.status = "部分付"
    else:
        bill.status = "未付"


def _reading_to_dict(r: MeterReading) -> dict:
    last = r.last_reading or 0
    current = r.current_reading or 0
    return {
        "id": r.id, "record_code": r.record_code,
        "contract_id": r.contract_id,
        "last_reading": r.last_reading, "current_reading": r.current_reading,
        "consumption": current - last if current >= last else 0,
        "electricity_amount": r.electricity_amount,
        "reading_date": r.reading_date, "meter_photo_path": r.meter_photo_path,
        "remark": r.remark, "created_at": r.created_at,
    }


def _resolve_last_reading(db: Session, contract_id: int) -> int:
    """获取上次读数：优先取最近一次抄表的 current_reading，否则取交房验收的电表底数。
    按 reading_date 排序（而非 id），正确处理补录历史数据的情况。"""
    last = db.scalar(select(MeterReading.current_reading).where(
        MeterReading.contract_id == contract_id,
    ).order_by(MeterReading.reading_date.desc(), MeterReading.id.desc()).limit(1))
    if last is not None:
        return last
    insp = db.scalar(select(MoveInInspection.meter_base_reading).where(
        MoveInInspection.contract_id == contract_id,
    ).limit(1))
    if insp is not None:
        return insp
    raise HTTPException(400, "未找到交房验收电表底数，请先完成交房验收")


def get_reading(db: Session, reading_id: int) -> dict:
    r = get_or_404(db, MeterReading, reading_id, "电表记录")
    return _reading_to_dict(r)


def list_readings(db: Session, contract_id: int) -> list[dict]:
    readings = list(db.scalars(
        select(MeterReading).where(MeterReading.contract_id == contract_id).order_by(MeterReading.reading_date.asc(), MeterReading.id.asc())
    ))
    results = []
    prev_reading = None
    for r in readings:
        warning = None
        if prev_reading is not None and r.last_reading is not None and r.last_reading != prev_reading:
            warning = f"上月读数应为{prev_reading}，当前记录为{r.last_reading}"
        d = _reading_to_dict(r)
        d["warning"] = warning
        results.append(d)
        prev_reading = r.current_reading
    return results


def create_reading(db: Session, data) -> dict:
    c = get_or_404(db, Contract, data.contract_id, "合同")
    check_status(c, {"已租", "退租处理中"}, "录入电表")

    # 当月只能抄表一次（用 substr 按月匹配，不依赖天数上限）
    reading_month = data.reading_date[:7] if len(data.reading_date) >= 7 else ""
    if reading_month:
        existing = db.scalar(select(MeterReading).where(
            MeterReading.contract_id == data.contract_id,
            func.substr(MeterReading.reading_date, 1, 7) == reading_month,
        ).limit(1))
        if existing:
            raise HTTPException(400, f"{reading_month} 当月已存在抄表记录（{existing.record_code}），每月只能抄表一次")

    last_reading = _resolve_last_reading(db, data.contract_id)
    if data.current_reading < last_reading:
        raise HTTPException(400, f"本次读数（{data.current_reading}）不能小于上次读数（{last_reading}）")

    consumption = data.current_reading - last_reading
    electricity_amount = round(ELECTRICITY_RATE * consumption, 10)

    r = MeterReading(
        record_code=next_code(db, MeterReading, MeterReading.record_code, "DB", 4),
        contract_id=data.contract_id,
        last_reading=last_reading,
        current_reading=data.current_reading,
        consumption=consumption,
        electricity_amount=electricity_amount,
        reading_date=data.reading_date,
        remark=data.remark,
    )
    db.add(r)
    db.commit()
    db.refresh(r)

    # 自动更新当月账单的电费
    bill = db.scalar(select(Bill).where(
        Bill.contract_id == data.contract_id,
        Bill.bill_month == reading_month,
    ))
    if bill:
        bill.electricity_fee = r.electricity_amount
        _recalculate_bill_total(db, bill)
        db.commit()

    return _reading_to_dict(r)


def update_reading(db: Session, reading_id: int, data) -> dict:
    r = get_or_404(db, MeterReading, reading_id, "电表记录")

    update_fields = data.model_dump(exclude_unset=True)
    old_current = r.current_reading
    current_changed = "current_reading" in update_fields and update_fields["current_reading"] != old_current

    # 应用更新
    for k, v in update_fields.items():
        setattr(r, k, v)

    # 当前读数变化 → 自动重算 consumption 和 electricity_amount
    if current_changed:
        last = r.last_reading or 0
        r.consumption = r.current_reading - last
        r.electricity_amount = round(ELECTRICITY_RATE * (r.current_reading - last), 2)

    db.flush()

    if current_changed:
        # 级联更新：同步下一笔的 last_reading 并重算其 consumption 和 electricity_amount
        next_reading = db.scalar(select(MeterReading).where(
            MeterReading.contract_id == r.contract_id,
            MeterReading.reading_date > r.reading_date,
        ).order_by(MeterReading.reading_date.asc(), MeterReading.id.asc()).limit(1))
        if next_reading:
            next_reading.last_reading = r.current_reading
            next_reading.consumption = next_reading.current_reading - r.current_reading
            next_reading.electricity_amount = round(ELECTRICITY_RATE * (next_reading.current_reading - r.current_reading), 2)

        # 级联更新：重算当月账单的电费
        reading_month = r.reading_date[:7] if r.reading_date else None
        if reading_month:
            bill = db.scalar(select(Bill).where(
                Bill.contract_id == r.contract_id,
                Bill.bill_month == reading_month,
            ))
            if bill:
                bill.electricity_fee = r.electricity_amount
                _recalculate_bill_total(db, bill)

    db.commit()
    db.refresh(r)
    return _reading_to_dict(r)


def upload_meter_photo(db: Session, reading_id: int, file: UploadFile) -> dict:
    r = get_or_404(db, MeterReading, reading_id, "电表记录")
    ext = validate_upload(file)
    filename = f"meter_{uuid.uuid4().hex[:8]}{ext}"
    rel = f"meter_readings/{filename}"
    abs_path = safe_write_upload(rel, file)
    try:
        r.meter_photo_path = rel
        db.commit()
    except Exception:
        os.remove(abs_path)
        raise
    db.refresh(r)
    return _reading_to_dict(r)
