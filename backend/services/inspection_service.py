"""
验收 Service — 交房验收 + 退房验收。
"""
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException, UploadFile
import os, shutil, uuid

from database import UPLOAD_DIR, validate_upload, safe_write_upload
from models.orm import (
    Contract, ContractItem, Property,
    MoveInInspection, MoveInInspectionItem, MoveInInspectionImage,
    MoveOutInspection, MoveOutInspectionItem, MoveOutInspectionImage,
    MeterReading,
)
from services.helpers import get_or_404, check_status, check_unique
from services.constants import ELECTRICITY_RATE


# ============================================================
# 交房验收
# ============================================================
def create_move_in_inspection(db: Session, data) -> dict:
    c = get_or_404(db, Contract, data.contract_id, "合同")
    check_status(c, {"待交房"}, "交房验收")
    check_unique(db, MoveInInspection, {"contract_id": data.contract_id}, "交房验收")

    insp = MoveInInspection(
        contract_id=data.contract_id,
        inspection_date=data.inspection_date,
        meter_base_reading=data.meter_base_reading,
        key_delivery_detail=data.key_delivery_detail,
    )
    db.add(insp)
    db.flush()

    # 从合同物品清单复制到验收明细
    items = list(db.scalars(
        select(ContractItem).where(ContractItem.contract_id == data.contract_id).order_by(ContractItem.sort_order)
    ))
    for item in items:
        db.add(MoveInInspectionItem(
            inspection_id=insp.id,
            item_name=item.item_name,
            quantity=item.quantity,
            status="完好",
        ))

    # 合同状态 → 已租，房产状态 → 已租
    c.status = "已租"
    prop = db.get(Property, c.property_id)
    if prop:
        prop.status = "已租"

    db.commit()
    return _get_move_in_inspection(db, insp.id)


def get_move_in_inspection(db: Session, contract_id: int) -> dict:
    insp = db.scalar(select(MoveInInspection).where(MoveInInspection.contract_id == contract_id))
    if not insp:
        raise HTTPException(404, "交房验收记录不存在")
    return _get_move_in_inspection(db, insp.id)


def _get_move_in_inspection(db: Session, inspection_id: int) -> dict:
    insp = db.get(MoveInInspection, inspection_id)
    items = list(db.scalars(
        select(MoveInInspectionItem).where(MoveInInspectionItem.inspection_id == inspection_id).order_by(MoveInInspectionItem.id)
    ))
    images = list(db.scalars(
        select(MoveInInspectionImage).where(MoveInInspectionImage.inspection_id == inspection_id).order_by(MoveInInspectionImage.sort_order)
    ))
    return {
        "id": insp.id, "contract_id": insp.contract_id,
        "inspection_date": insp.inspection_date,
        "meter_base_reading": insp.meter_base_reading,
        "key_delivery_detail": insp.key_delivery_detail,
        "meter_photo_path": insp.meter_photo_path,
        "landlord_signature_path": insp.landlord_signature_path,
        "tenant_signature_path": insp.tenant_signature_path,
        "created_at": insp.created_at,
        "items": [{"id": i.id, "item_name": i.item_name, "quantity": i.quantity, "status": i.status, "defect_remark": i.defect_remark} for i in items],
        "images": [{"id": i.id, "image_path": i.image_path, "sort_order": i.sort_order} for i in images],
    }


def update_move_in_item(db: Session, inspection_id: int, item_id: int, data) -> dict:
    item = get_or_404(db, MoveInInspectionItem, item_id, "物品")
    if item.inspection_id != inspection_id:
        raise HTTPException(404, "物品不存在")
    if data.status not in ("完好", "有瑕疵"):
        raise HTTPException(400, "物品状态必须为 完好/有瑕疵")
    item.status = data.status
    item.defect_remark = data.defect_remark
    db.commit()
    return _get_move_in_inspection(db, inspection_id)


def upload_move_in_image(db: Session, inspection_id: int, file: UploadFile) -> dict:
    insp = get_or_404(db, MoveInInspection, inspection_id, "验收记录")
    ext = validate_upload(file)
    filename = f"move_in_{uuid.uuid4().hex[:8]}{ext}"
    rel = f"inspections/{filename}"
    abs_path = safe_write_upload(rel, file)
    try:
        max_order = db.scalar(select(MoveInInspectionImage.sort_order).where(
            MoveInInspectionImage.inspection_id == inspection_id
        ).order_by(MoveInInspectionImage.sort_order.desc()).limit(1)) or 0
        db.add(MoveInInspectionImage(inspection_id=inspection_id, image_path=rel, sort_order=(max_order or 0) + 1))
        db.commit()
    except Exception:
        os.remove(abs_path)
        raise
    return _get_move_in_inspection(db, inspection_id)


def upload_move_in_signature(db: Session, inspection_id: int, role: str, file: UploadFile) -> dict:
    """role: 'landlord' or 'tenant'"""
    insp = get_or_404(db, MoveInInspection, inspection_id, "验收记录")
    ext = validate_upload(file)
    filename = f"sig_{role}_{uuid.uuid4().hex[:8]}{ext}"
    rel = f"signatures/{filename}"
    abs_path = safe_write_upload(rel, file)
    try:
        if role == "landlord":
            insp.landlord_signature_path = rel
        else:
            insp.tenant_signature_path = rel
        db.commit()
    except Exception:
        os.remove(abs_path)
        raise
    return _get_move_in_inspection(db, inspection_id)


# ============================================================
# 退房验收
# ============================================================
def create_move_out_inspection(db: Session, data) -> dict:
    c = get_or_404(db, Contract, data.contract_id, "合同")
    check_status(c, {"退租处理中"}, "退房验收")
    check_unique(db, MoveOutInspection, {"contract_id": data.contract_id}, "退房验收")

    # 自动计算电费扣款：最后一条抄表读数 → (当前读数 - 最后读数) × 单价
    last_reading = db.scalar(select(MeterReading.current_reading).where(
        MeterReading.contract_id == data.contract_id,
    ).order_by(MeterReading.id.desc()).limit(1))
    if last_reading is not None:
        if data.meter_reading < last_reading:
            raise HTTPException(400, f"电表读数（{data.meter_reading}）不能小于最后一次抄表读数（{last_reading}），电费不能为负数")
        electricity_deduction = round((data.meter_reading - last_reading) * ELECTRICITY_RATE, 10)
    else:
        # 无抄表记录，使用交房底数
        base = db.scalar(select(MoveInInspection.meter_base_reading).where(
            MoveInInspection.contract_id == data.contract_id))
        if base is not None:
            if data.meter_reading < base:
                raise HTTPException(400, f"电表读数（{data.meter_reading}）不能小于交房底数（{base}），电费不能为负数")
            electricity_deduction = round((data.meter_reading - base) * ELECTRICITY_RATE, 10)
        else:
            electricity_deduction = 0

    if electricity_deduction < 0:
        raise HTTPException(400, f"电费扣款不能为负数（当前：{electricity_deduction}），请检查电表读数")

    insp = MoveOutInspection(
        contract_id=data.contract_id,
        inspection_date=data.inspection_date,
        meter_reading=data.meter_reading,
        electricity_deduction=electricity_deduction,
        key_return_status=data.key_return_status,
        key_deduction=data.key_deduction,
        remark=data.remark,
    )
    db.add(insp)
    db.flush()

    # 从合同物品清单复制到退房验收明细
    items = list(db.scalars(
        select(ContractItem).where(ContractItem.contract_id == data.contract_id).order_by(ContractItem.sort_order)
    ))
    for item in items:
        db.add(MoveOutInspectionItem(
            inspection_id=insp.id,
            item_name=item.item_name,
            quantity=item.quantity,
            status="完好",
        ))

    db.commit()
    return _get_move_out_inspection(db, insp.id)


def get_move_out_inspection(db: Session, contract_id: int) -> dict:
    insp = db.scalar(select(MoveOutInspection).where(MoveOutInspection.contract_id == contract_id))
    if not insp:
        raise HTTPException(404, "退房验收记录不存在")
    return _get_move_out_inspection(db, insp.id)


def _get_move_out_inspection(db: Session, inspection_id: int) -> dict:
    insp = db.get(MoveOutInspection, inspection_id)
    items = list(db.scalars(
        select(MoveOutInspectionItem).where(MoveOutInspectionItem.inspection_id == inspection_id).order_by(MoveOutInspectionItem.id)
    ))
    images = list(db.scalars(
        select(MoveOutInspectionImage).where(MoveOutInspectionImage.inspection_id == inspection_id).order_by(MoveOutInspectionImage.sort_order)
    ))
    return {
        "id": insp.id, "contract_id": insp.contract_id,
        "inspection_date": insp.inspection_date,
        "meter_reading": insp.meter_reading,
        "electricity_deduction": insp.electricity_deduction,
        "key_return_status": insp.key_return_status,
        "key_deduction": insp.key_deduction, "remark": insp.remark,
        "created_at": insp.created_at,
        "items": [{"id": i.id, "item_name": i.item_name, "quantity": i.quantity, "status": i.status, "deduction_amount": i.deduction_amount} for i in items],
        "images": [{"id": i.id, "image_path": i.image_path, "sort_order": i.sort_order} for i in images],
    }


def update_move_out_item(db: Session, inspection_id: int, item_id: int, data) -> dict:
    item = get_or_404(db, MoveOutInspectionItem, item_id, "物品")
    if item.inspection_id != inspection_id:
        raise HTTPException(404, "物品不存在")
    if data.status not in ("完好", "损坏", "缺失"):
        raise HTTPException(400, "物品状态必须为 完好/损坏/缺失")
    if data.deduction_amount < 0:
        raise HTTPException(400, "扣款金额不能为负数")
    item.status = data.status
    item.deduction_amount = data.deduction_amount
    db.commit()

    # 自动更新未确认的结算单中的物品扣款
    insp = db.get(MoveOutInspection, inspection_id)
    if insp:
        from models.orm import Settlement
        s = db.scalar(select(Settlement).where(
            Settlement.contract_id == insp.contract_id))
        if s and not s.settled_at:
            item_damage, item_missing = 0, 0
            for it in db.scalars(select(MoveOutInspectionItem).where(
                MoveOutInspectionItem.inspection_id == inspection_id)):
                if it.status == "损坏":
                    item_damage += it.deduction_amount
                elif it.status == "缺失":
                    item_missing += it.deduction_amount
            s.item_damage_deduction = item_damage
            s.item_missing_deduction = item_missing
            db.commit()

    return _get_move_out_inspection(db, inspection_id)



def update_move_out_inspection(db: Session, inspection_id: int, data) -> dict:
    """编辑退房验收信息，自动重算电费并同步未确认的结算单。"""
    insp = get_or_404(db, MoveOutInspection, inspection_id, "验收记录")

    if data.inspection_date is not None:
        insp.inspection_date = data.inspection_date

    if data.meter_reading is not None:
        # 重新计算电费扣款
        last_reading = db.scalar(select(MeterReading.current_reading).where(
            MeterReading.contract_id == insp.contract_id,
        ).order_by(MeterReading.id.desc()).limit(1))
        if last_reading is not None:
            if data.meter_reading < last_reading:
                raise HTTPException(400, f"电表读数（{data.meter_reading}）不能小于最后一次抄表读数（{last_reading}），电费不能为负数")
            electricity = round((data.meter_reading - last_reading) * ELECTRICITY_RATE, 10)
        else:
            base = db.scalar(select(MoveInInspection.meter_base_reading).where(
                MoveInInspection.contract_id == insp.contract_id))
            if base is not None:
                if data.meter_reading < base:
                    raise HTTPException(400, f"电表读数（{data.meter_reading}）不能小于交房底数（{base}），电费不能为负数")
                electricity = round((data.meter_reading - base) * ELECTRICITY_RATE, 10)
            else:
                electricity = 0

        if electricity < 0:
            raise HTTPException(400, f"电费扣款不能为负数（当前：{electricity}），请检查电表读数")

        insp.meter_reading = data.meter_reading
        insp.electricity_deduction = electricity

    if data.key_return_status is not None:
        insp.key_return_status = data.key_return_status

    if data.key_deduction is not None:
        insp.key_deduction = data.key_deduction

    if data.remark is not None:
        insp.remark = data.remark

    db.commit()
    db.refresh(insp)

    # 同步更新未确认的结算单
    from models.orm import Settlement
    s = db.scalar(select(Settlement).where(
        Settlement.contract_id == insp.contract_id))
    if s and not s.settled_at:
        s.electricity_deduction = insp.electricity_deduction
        s.key_deduction = insp.key_deduction
        db.commit()

    return _get_move_out_inspection(db, inspection_id)


def update_move_out_key_deduction(db: Session, inspection_id: int, data) -> dict:
    """更新退房验收的钥匙扣款金额，并同步更新未确认的结算单。"""
    insp = get_or_404(db, MoveOutInspection, inspection_id, "验收记录")
    insp.key_deduction = data.key_deduction
    db.commit()

    # 同步更新未确认的结算单
    from models.orm import Settlement
    s = db.scalar(select(Settlement).where(
        Settlement.contract_id == insp.contract_id))
    if s and not s.settled_at:
        s.key_deduction = data.key_deduction
        db.commit()

    return _get_move_out_inspection(db, inspection_id)


def upload_move_out_image(db: Session, inspection_id: int, file: UploadFile) -> dict:
    insp = get_or_404(db, MoveOutInspection, inspection_id, "验收记录")
    ext = validate_upload(file)
    filename = f"move_out_{uuid.uuid4().hex[:8]}{ext}"
    rel = f"inspections/{filename}"
    abs_path = safe_write_upload(rel, file)
    try:
        max_order = db.scalar(select(MoveOutInspectionImage.sort_order).where(
            MoveOutInspectionImage.inspection_id == inspection_id
        ).order_by(MoveOutInspectionImage.sort_order.desc()).limit(1)) or 0
        db.add(MoveOutInspectionImage(inspection_id=inspection_id, image_path=rel, sort_order=(max_order or 0) + 1))
        db.commit()
    except Exception:
        os.remove(abs_path)
        raise
    return _get_move_out_inspection(db, inspection_id)
