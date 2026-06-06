"""
账单 Service。
"""
import json
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException

from models.orm import (Bill, BillOtherFee, Contract, ContractItem, MeterReading,
                        Property, Tenant, PaymentAllocation, Payment, DunningLog)
from database import beijing_now
from services.helpers import get_or_404, next_code_ym, check_status, check_unique
from services.constants import ELECTRICITY_RATE, beijing_today_str


def _bill_to_dict(b: Bill, prop_name: str = "", tenant_name: str = "", tenant_phone: str = "",
                  contract_code: str = "", other_fees: list[BillOtherFee] | None = None,
                  paid_amount: int = 0) -> dict:
    other_fee = sum(f.amount for f in (other_fees or []))
    return {
        "id": b.id, "bill_code": b.bill_code,
        "contract_id": b.contract_id, "contract_code": contract_code,
        "property_name": prop_name, "tenant_name": tenant_name, "tenant_phone": tenant_phone,
        "bill_month": b.bill_month,
        "rent": b.rent, "water_fee": b.water_fee,
        "electricity_fee": b.electricity_fee, "other_fee": other_fee,
        "total": b.total, "paid_amount": paid_amount,
        "generated_date": b.generated_date, "due_date": b.due_date,
        "status": b.status, "remark": b.remark, "created_at": b.created_at,
        "other_fees": [{"id": f.id, "fee_name": f.fee_name, "amount": f.amount, "remark": f.remark}
                       for f in (other_fees or [])],
    }


def unpaid_bills_summary(db: Session, contract_id: int) -> tuple[int, str]:
    """Return (unpaid_total, unpaid_note) for a contract's unpaid/partial bills."""
    bills = list(db.scalars(select(Bill).where(
        Bill.contract_id == contract_id, Bill.status.in_(("未付", "部分付"))
    )))
    if not bills:
        return 0, ""
    bill_ids = [b.id for b in bills]
    rows = db.execute(
        select(PaymentAllocation.bill_id, func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .where(PaymentAllocation.bill_id.in_(bill_ids)).group_by(PaymentAllocation.bill_id)
    ).all()
    alloc_sums = {row[0]: row[1] for row in rows}
    total = round(sum(max(0, (b.total or 0) - alloc_sums.get(b.id, 0)) for b in bills), 2)
    note = "；".join(
        f"{b.bill_month}(欠{max(0, round((b.total or 0) - alloc_sums.get(b.id, 0), 2))}元)" for b in bills
    )
    return total, note


def _generate_bill_for_month(db: Session, c: Contract, bill_month: str) -> Bill | None:
    """为指定合同生成单月账单。合同必须已应用待生效变更。返回 None 表示跳过（月份已存在）。"""
    import calendar

    current_month = beijing_now().strftime("%Y-%m")
    if bill_month > current_month:
        return None  # 不生成未来月份

    if bill_month < c.start_date[:7] or bill_month > c.end_date[:7]:
        return None  # 不在合同有效期内

    existing = db.scalar(select(Bill).where(
        Bill.contract_id == c.id, Bill.bill_month == bill_month))
    if existing:
        return None  # 已存在，跳过

    ym = bill_month
    year, month = int(ym[:4]), int(ym[5:7])
    max_day = calendar.monthrange(year, month)[1]

    reading = db.scalar(select(MeterReading).where(
        MeterReading.contract_id == c.id,
        MeterReading.reading_date >= f"{ym}-01",
        MeterReading.reading_date <= f"{ym}-{max_day:02d}",
    ).order_by(MeterReading.reading_date.desc()).limit(1))
    electricity_fee = 0
    if reading:
        electricity_fee = reading.electricity_amount or (
            round(reading.consumption * ELECTRICITY_RATE, 10) if reading.consumption else 0)

    due_day = min(c.rent_due_day, max_day)
    # 交租日可能晚于抄表日，账单生成后给用户足够的付款时间
    due_date = f"{year}-{month:02d}-{due_day:02d}"
    # 如果交租日已过（比如今天是5月1日但账单是4月的），due_date 设为生成日+7天
    if due_date < beijing_today_str():
        from datetime import timedelta
        due_date = (beijing_now() + timedelta(days=7)).strftime("%Y-%m-%d")

    b = Bill(
        bill_code=next_code_ym(db, Bill, Bill.bill_code, "ZD"),
        contract_id=c.id,
        bill_month=bill_month,
        rent=c.monthly_rent, water_fee=c.water_fee,
        electricity_fee=electricity_fee,
        total=round(c.monthly_rent + c.water_fee + electricity_fee, 10),
        generated_date=beijing_now().strftime("%Y-%m-%d %H:%M:%S"),
        due_date=due_date, status="未付",
    )
    db.add(b)
    return b


def generate_bill(db: Session, contract_id: int, data) -> dict:
    c = get_or_404(db, Contract, contract_id, "合同")
    check_status(c, {"已租", "退租处理中"}, "生成账单")

    from services.contract_service import _apply_pending_changes as _apply_pending
    _apply_pending(c)

    b = _generate_bill_for_month(db, c, data.bill_month)
    if b is None:
        raise HTTPException(400, f"账单月份（{data.bill_month}）无效、已存在或不在合同有效期内")

    db.commit()
    db.refresh(b)
    prop = db.get(Property, c.property_id)
    tenant = db.get(Tenant, c.tenant_id_number)
    return _bill_to_dict(b, prop.name if prop else "", tenant.name if tenant else "",
                         tenant.phone if tenant else "", c.contract_code)


def auto_generate_bills(db: Session, contract_id: int | None = None) -> dict:
    """自动为活跃合同生成所有缺失月份的账单。进入账单模块时调用。"""
    from services.contract_service import _apply_pending_changes as _apply_pending

    stmt = select(Contract).where(Contract.status.in_(("已租", "退租处理中")))
    if contract_id:
        stmt = stmt.where(Contract.id == contract_id)
    contracts = list(db.scalars(stmt))

    current_month = beijing_now().strftime("%Y-%m")
    generated = 0
    skipped = 0
    error_msgs = []

    for c in contracts:
        try:
            _apply_pending(c)
        except Exception:
            pass

        # skip contracts with obviously bad dates
        try:
            sy, sm = int(c.start_date[:4]), int(c.start_date[5:7])
            ey, em = int(c.end_date[:4]), int(c.end_date[5:7])
        except (ValueError, IndexError):
            continue
        if sy < 2000 or ey < 2000:
            continue

        existing = set(row[0] for row in db.execute(
            select(Bill.bill_month).where(Bill.contract_id == c.id)
        ).all())

        start_ym = c.start_date[:7]
        end_ym = min(c.end_date[:7], current_month)

        ym_year, ym_month = sy, sm
        while (ym_year < ey) or (ym_year == ey and ym_month <= em):
            bill_month = f"{ym_year}-{ym_month:02d}"
            if bill_month > current_month:
                break
            if bill_month not in existing:
                b = _generate_bill_for_month(db, c, bill_month)
                if b is not None:
                    db.flush()
                    generated += 1
            else:
                skipped += 1

            ym_month += 1
            if ym_month > 12:
                ym_month = 1
                ym_year += 1

    db.commit()
    return {"generated": generated, "skipped": skipped, "errors": error_msgs}


def list_bills(db: Session, contract_id: int | None = None,
               contract_ids: list[int] | None = None, status: str | None = None) -> list[dict]:
    stmt = select(Bill).order_by(Bill.bill_month.desc())
    if contract_id:
        stmt = stmt.where(Bill.contract_id == contract_id)
    if contract_ids:
        stmt = stmt.where(Bill.contract_id.in_(contract_ids))
    # 使用北京时间而非服务器本地时间，保证跨时区部署一致性
    today = beijing_today_str()
    if status:
        if status == "逾期":
            stmt = stmt.where(
                Bill.status.in_(("未付", "部分付")),
                Bill.due_date < today,
            )
        elif status in ("未付", "部分付"):
            # 显示所有该状态的账单，前端可以按 due_date 标记逾期
            stmt = stmt.where(Bill.status == status)
        else:
            stmt = stmt.where(Bill.status == status)
    bills = list(db.scalars(stmt))
    if not bills:
        return []

    # 批量预加载关联数据
    c_ids = list(set(b.contract_id for b in bills))
    contracts = {c.id: c for c in db.scalars(select(Contract).where(Contract.id.in_(c_ids)))}
    p_ids = [c.property_id for c in contracts.values()]
    t_ids = [c.tenant_id_number for c in contracts.values()]
    props = {p.id: p for p in db.scalars(select(Property).where(Property.id.in_(p_ids)))}
    tenants = {t.id_number: t for t in db.scalars(select(Tenant).where(Tenant.id_number.in_(t_ids)))}

    all_fees = list(db.scalars(select(BillOtherFee).where(
        BillOtherFee.bill_id.in_([b.id for b in bills]))))
    fee_map: dict[int, list] = {}
    for f in all_fees:
        fee_map.setdefault(f.bill_id, []).append(f)

    bill_ids = [b.id for b in bills]
    alloc_rows = db.execute(
        select(PaymentAllocation.bill_id, func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .where(PaymentAllocation.bill_id.in_(bill_ids)).group_by(PaymentAllocation.bill_id)
    ).all()
    paid_map: dict[int, int] = {row[0]: row[1] for row in alloc_rows}

    results = []
    for b in bills:
        ct = contracts.get(b.contract_id)
        p = props.get(ct.property_id) if ct else None
        t = tenants.get(ct.tenant_id_number) if ct else None
        results.append(_bill_to_dict(b, p.name if p else "", t.name if t else "",
                                      t.phone if t else "", ct.contract_code if ct else "",
                                      fee_map.get(b.id, []), paid_map.get(b.id, 0)))
    return results


def get_bill(db: Session, bill_id: int) -> dict:
    b = get_or_404(db, Bill, bill_id, "账单")
    ct = db.get(Contract, b.contract_id)
    p = db.get(Property, ct.property_id) if ct else None
    t = db.get(Tenant, ct.tenant_id_number) if ct else None
    other_fees = list(db.scalars(select(BillOtherFee).where(BillOtherFee.bill_id == bill_id)))
    paid = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .where(PaymentAllocation.bill_id == bill_id)
    ) or 0
    return _bill_to_dict(b, p.name if p else "", t.name if t else "",
                         t.phone if t else "", ct.contract_code if ct else "", other_fees, paid)


def add_other_fee(db: Session, bill_id: int, data) -> dict:
    b = get_or_404(db, Bill, bill_id, "账单")
    if b.status == "已付":
        raise HTTPException(400, "账单已付，无法追加费用")
    check_unique(db, BillOtherFee, {"bill_id": bill_id, "fee_name": data.fee_name}, "费用项")
    db.add(BillOtherFee(bill_id=bill_id, fee_name=data.fee_name, amount=data.amount, remark=data.remark))
    db.flush()
    total_other = db.scalar(
        select(func.coalesce(func.sum(BillOtherFee.amount), 0))
        .where(BillOtherFee.bill_id == bill_id)
    ) or 0
    b.total = round(b.rent + b.water_fee + b.electricity_fee + total_other, 10)
    # 总额变化后重算状态
    paid = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .where(PaymentAllocation.bill_id == bill_id)
    ) or 0
    if paid >= b.total:
        b.status = "已付"
    elif paid > 0:
        b.status = "部分付"
    db.commit()
    db.refresh(b)
    return get_bill(db, bill_id)


def get_bill_payments(db: Session, bill_id: int) -> list[dict]:
    get_or_404(db, Bill, bill_id, "账单")
    rows = db.execute(
        select(Payment, PaymentAllocation.amount)
        .join(PaymentAllocation, PaymentAllocation.payment_id == Payment.id)
        .where(PaymentAllocation.bill_id == bill_id)
        .order_by(Payment.payment_date.desc())
    ).all()
    return [{
        "id": p.id, "payment_date": p.payment_date,
        "amount": alloc_amount, "total_amount": p.total_amount,
        "payment_method": p.payment_method, "remark": p.remark,
        "created_at": p.created_at,
    } for p, alloc_amount in rows]


def send_dunning(db: Session, bill_id: int, data) -> dict:
    b = get_or_404(db, Bill, bill_id, "账单")
    if b.status == "已付":
        raise HTTPException(400, "账单已付，无需催收")
    db.add(DunningLog(bill_id=bill_id, sms_content=data.sms_content))
    db.commit()
    return get_bill(db, bill_id)
