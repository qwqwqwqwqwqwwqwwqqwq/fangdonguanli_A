"""
结算单 Service。
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException

from database import beijing_now_str
from models.orm import (Settlement, Contract, MoveOutInspection, MoveOutInspectionItem, Property, Tenant)
from services.helpers import get_or_404, check_status
from services.bill_service import unpaid_bills_summary

BEIJING_TZ = timezone(timedelta(hours=8))


def _settlement_to_dict(s: Settlement) -> dict:
    # 已确认的结算单使用持久化的 actual_refund，未确认时实时计算
    if s.actual_refund is not None:
        actual_refund = s.actual_refund
    else:
        actual_refund = round((s.deposit_total - s.electricity_deduction - s.item_damage_deduction
                         - s.item_missing_deduction - s.key_deduction
                         - s.unpaid_bills_total - s.other_deduction), 2)
    return {
        "id": s.id, "contract_id": s.contract_id,
        "deposit_total": s.deposit_total,
        "electricity_deduction": s.electricity_deduction,
        "item_damage_deduction": s.item_damage_deduction,
        "item_missing_deduction": s.item_missing_deduction,
        "key_deduction": s.key_deduction,
        "unpaid_bills_note": s.unpaid_bills_note,
        "unpaid_bills_total": s.unpaid_bills_total,
        "other_deduction": s.other_deduction,
        "actual_refund": actual_refund,
        "refund_date": s.refund_date, "refund_method": s.refund_method,
        "remark": s.remark, "created_at": s.created_at,
        "settled_at": s.settled_at,
    }


def create_settlement(db: Session, contract_id: int, data) -> dict:
    c = get_or_404(db, Contract, contract_id, "合同")
    check_status(c, {"退租处理中"}, "生成结算单")

    # 如已有未确认的结算单，先删除再重新生成（允许更新物品后重新计算）
    existing = db.scalar(select(Settlement).where(Settlement.contract_id == contract_id))
    if existing:
        if existing.settled_at:
            raise HTTPException(400, "结算单已确认，无法重新生成")
        db.delete(existing)
        db.flush()

    insp = db.scalar(select(MoveOutInspection).where(
        MoveOutInspection.contract_id == contract_id))
    if not insp:
        raise HTTPException(400, "请先完成退房验收后再生成结算单")

    # 物品扣款汇总
    item_damage, item_missing = 0, 0
    for item in list(db.scalars(select(MoveOutInspectionItem).where(
        MoveOutInspectionItem.inspection_id == insp.id))):
        if item.status == "损坏":
            item_damage += item.deduction_amount
        elif item.status == "缺失":
            item_missing += item.deduction_amount

    # 未付账单汇总
    unpaid_total, unpaid_note = unpaid_bills_summary(db, contract_id)

    s = Settlement(
        contract_id=contract_id, deposit_total=c.deposit,
        electricity_deduction=insp.electricity_deduction,
        item_damage_deduction=item_damage,
        item_missing_deduction=item_missing,
        key_deduction=insp.key_deduction,
        unpaid_bills_note=unpaid_note,
        unpaid_bills_total=unpaid_total,
        other_deduction=data.other_deduction,
        remark=data.remark,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _settlement_to_dict(s)


def get_settlement(db: Session, contract_id: int) -> dict:
    s = db.scalar(select(Settlement).where(Settlement.contract_id == contract_id))
    if not s:
        raise HTTPException(404, "结算单不存在")
    return _settlement_to_dict(s)


def confirm_settlement(db: Session, contract_id: int, data) -> dict:
    s = db.scalar(select(Settlement).where(Settlement.contract_id == contract_id))
    if not s:
        raise HTTPException(404, "结算单不存在")
    if s.settled_at:
        raise HTTPException(400, "结算单已确认，无法重复操作")

    try:
        refund_dt = datetime.strptime(data.refund_date, "%Y-%m-%d").replace(tzinfo=BEIJING_TZ)
        now = datetime.now(BEIJING_TZ)
        if refund_dt > now + timedelta(days=7):
            raise HTTPException(400, "退款日期不能在未来7天之后")
        if refund_dt < now - timedelta(days=30):
            raise HTTPException(400, "退款日期不能早于30天前")
    except ValueError:
        raise HTTPException(400, "退款日期格式无效，请使用 YYYY-MM-DD 格式")

    # 持久化 actual_refund，确认后不再实时重算，防止扣款项被篡改
    actual_refund = round((s.deposit_total - s.electricity_deduction - s.item_damage_deduction
                           - s.item_missing_deduction - s.key_deduction
                           - s.unpaid_bills_total - s.other_deduction), 2)
    if actual_refund < 0:
        raise HTTPException(400, f"押金不足以覆盖扣款（差额{-actual_refund}元），请先调整扣款项")

    s.refund_date = data.refund_date
    s.refund_method = data.refund_method
    s.remark = data.remark or s.remark
    s.settled_at = beijing_now_str()
    s.actual_refund = actual_refund

    result = _settlement_to_dict(s)

    c = db.get(Contract, contract_id)
    if not c:
        raise HTTPException(404, "合同不存在")
    tenant_id = c.tenant_id_number
    property_id = c.property_id

    # 释放房产
    if property_id:
        prop = db.get(Property, property_id)
        if prop:
            prop.status = "空闲"

    # 租客标记为已退租
    if tenant_id:
        other = db.scalar(select(Contract.id).where(
            Contract.tenant_id_number == tenant_id, Contract.id != contract_id,
            Contract.status.in_(("待交房", "已租", "退租处理中"))).limit(1))
        if not other:
            tenant = db.get(Tenant, tenant_id)
            if tenant:
                tenant.status = "已退租"
                tenant.archived_at = beijing_now_str()

    # 软删除：合同标记为已结算，保留所有历史数据
    c.status = "已结算-已退租"

    db.commit()
    return result
