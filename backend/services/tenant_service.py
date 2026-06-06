"""
租客 Service — 业务逻辑层。
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case, or_
from fastapi import HTTPException

from models.orm import (Tenant, Contract, Bill, Property, PaymentAllocation, Payment,
                        MeterReading, MoveInInspection, MoveInInspectionItem,
                        MoveOutInspection, MoveOutInspectionItem, Settlement, ContractItem)
from models.schemas import (TenantCreate, TenantUpdate, TenantCreditResponse,
                            TenantProfileResponse, TenantProfileContract, CleanupResponse)
from services.helpers import get_or_404
from services.constants import beijing_today_str

BEIJING_TZ = timezone(timedelta(hours=8))


def _five_months_ago() -> str:
    """每次调用时动态计算，避免模块加载时冻结时间。"""
    return (datetime.now(BEIJING_TZ) - timedelta(days=150)).strftime("%Y-%m-%d %H:%M:%S")


def list_tenants(db: Session) -> list[Tenant]:
    return list(db.scalars(select(Tenant).order_by(Tenant.id_number)))


def get_tenant(db: Session, id_number: str) -> Tenant:
    return get_or_404(db, Tenant, id_number, "租客")


def create_tenant(db: Session, data: TenantCreate) -> Tenant:
    if db.get(Tenant, data.id_number):
        raise HTTPException(400, "该身份证号已存在")
    t = Tenant(id_number=data.id_number, name=data.name, phone=data.phone, remark=data.remark)
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def update_tenant(db: Session, id_number: str, data: TenantUpdate) -> Tenant:
    t = get_tenant(db, id_number)
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(t, k, v)
    db.commit()
    db.refresh(t)
    return t


def delete_tenant(db: Session, id_number: str) -> None:
    t = get_tenant(db, id_number)
    from services.property_service import _check_any_contract
    _check_any_contract(db, "tenant_id_number", id_number)
    db.delete(t)
    db.commit()


def get_credit(db: Session, id_number: str) -> dict:
    t = get_tenant(db, id_number)
    result = db.execute(
        select(
            func.count(Bill.id),
            func.sum(case((Bill.status.in_(("未付", "部分付")), 1), else_=0))
        )
        .join(Contract, Bill.contract_id == Contract.id)
        .where(
            Contract.tenant_id_number == id_number,
            Bill.due_date < beijing_today_str(),
        )
    ).one()
    total_overdue, current_overdue = result[0] or 0, result[1] or 0
    return TenantCreditResponse(
        id_number=t.id_number, name=t.name, phone=t.phone,
        current_overdue_count=current_overdue,
        has_current_overdue="是" if current_overdue > 0 else "否",
        total_overdue_count=total_overdue,
    ).model_dump()


def _days_between(start: str, end: str) -> int:
    """计算两个 YYYY-MM-DD 日期之间的天数（含首尾）。"""
    try:
        from datetime import date
        s = date(int(start[:4]), int(start[5:7]), int(start[8:10]))
        e = date(int(end[:4]), int(end[5:7]), int(end[8:10]))
        return max(1, (e - s).days + 1)
    except (ValueError, IndexError):
        return 0


def get_tenant_profile(db: Session, id_number: str) -> dict:
    """返回租客完整档案：个人信息 + 合同历史 + 账单缴费统计。"""
    t = get_tenant(db, id_number)

    contracts = list(db.scalars(
        select(Contract).where(Contract.tenant_id_number == id_number)
        .order_by(Contract.start_date.desc())
    ))

    property_ids = list(set(c.property_id for c in contracts))
    property_map = {p.id: p for p in db.scalars(
        select(Property).where(Property.id.in_(property_ids))
    )} if property_ids else {}

    # 账单汇总 — 通过 Contract -> Bill -> PaymentAllocation
    contract_ids = [c.id for c in contracts]
    total_billed = 0
    total_paid = 0
    overdue_count = 0
    bill_map: dict[int, list] = {}  # contract_id -> [bills]
    if contract_ids:
        bills = list(db.scalars(select(Bill).where(Bill.contract_id.in_(contract_ids))))
        bill_ids = [b.id for b in bills]
        total_billed = sum(b.total or 0 for b in bills)

        # 逾期计数
        now_date = datetime.now(BEIJING_TZ).strftime("%Y-%m-%d")
        overdue_count = sum(1 for b in bills
                           if b.status in ("未付", "部分付") and b.due_date < now_date)

        # 已收总额
        if bill_ids:
            alloc_rows = db.execute(
                select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
                .where(PaymentAllocation.bill_id.in_(bill_ids))
            ).scalar() or 0
            total_paid = alloc_rows

        for b in bills:
            bill_map.setdefault(b.contract_id, []).append(b)

    # 一次性查询所有合同的已收金额，避免 N+1
    c_paid_map: dict[int, int] = {}
    if contract_ids and bill_ids:
        rows = db.execute(
            select(Bill.contract_id, func.coalesce(func.sum(PaymentAllocation.amount), 0))
            .join(PaymentAllocation, PaymentAllocation.bill_id == Bill.id)
            .where(Bill.id.in_(bill_ids))
            .group_by(Bill.contract_id)
        ).all()
        c_paid_map = {row[0]: row[1] for row in rows}

    # 组装合同列表
    contract_list = []
    current_contract = None
    for c in contracts:
        prop = property_map.get(c.property_id)
        c_bills = bill_map.get(c.id, [])
        c_billed = sum(b.total or 0 for b in c_bills)
        c_paid = c_paid_map.get(c.id, 0)

        # Load detailed history
        c_meter_readings = list(db.scalars(
            select(MeterReading).where(MeterReading.contract_id == c.id)
            .order_by(MeterReading.reading_date.asc())
        ))
        c_move_in = db.scalar(
            select(MoveInInspection).where(MoveInInspection.contract_id == c.id))
        c_move_in_items = []
        if c_move_in:
            c_move_in_items = list(db.scalars(
                select(MoveInInspectionItem).where(MoveInInspectionItem.inspection_id == c_move_in.id)
            ))
        c_move_out = db.scalar(
            select(MoveOutInspection).where(MoveOutInspection.contract_id == c.id))
        c_move_out_items = []
        if c_move_out:
            c_move_out_items = list(db.scalars(
                select(MoveOutInspectionItem).where(MoveOutInspectionItem.inspection_id == c_move_out.id)
            ))
        c_settlement = db.scalar(
            select(Settlement).where(Settlement.contract_id == c.id))
        c_items = list(db.scalars(
            select(ContractItem).where(ContractItem.contract_id == c.id)
            .order_by(ContractItem.sort_order)
        ))
        # Payments for this contract
        c_pay_ids = []
        if c_bills:
            c_pay_ids = list(db.execute(
                select(PaymentAllocation.payment_id).where(
                    PaymentAllocation.bill_id.in_([b.id for b in c_bills]))
            ).scalars().all())
        c_payments = []
        if c_pay_ids:
            c_payments = list(db.scalars(
                select(Payment).where(Payment.id.in_(list(set(c_pay_ids))))
            ))
        # Per-bill paid mapping
        c_bill_paid = {}
        if c_bills:
            c_bill_ids = [b.id for b in c_bills]
            if c_bill_ids:
                rows = db.execute(
                    select(PaymentAllocation.bill_id, func.coalesce(func.sum(PaymentAllocation.amount), 0))
                    .where(PaymentAllocation.bill_id.in_(c_bill_ids))
                    .group_by(PaymentAllocation.bill_id)
                ).all()
                c_bill_paid = {row[0]: row[1] for row in rows}

        item = TenantProfileContract(
            contract_id=c.id,
            contract_code=c.contract_code,
            property_name=prop.name if prop else "",
            start_date=c.start_date,
            end_date=c.end_date,
            status=c.status,
            days_rented=_days_between(c.start_date, c.end_date),
            total_billed=c_billed,
            total_paid=c_paid,
            has_unpaid=c_paid < c_billed,
            meter_readings=[{
                "reading_date": mr.reading_date,
                "current_reading": mr.current_reading,
                "consumption": mr.consumption or 0,
                "electricity_amount": mr.electricity_amount,
            } for mr in c_meter_readings],
            bills=[{
                "bill_code": b.bill_code,
                "bill_month": b.bill_month,
                "rent": b.rent,
                "water_fee": b.water_fee,
                "electricity_fee": b.electricity_fee,
                "total": b.total,
                "status": b.status,
                "paid_amount": c_bill_paid.get(b.id, 0),
            } for b in c_bills],
            move_in_inspection={
                "inspection_date": c_move_in.inspection_date,
                "meter_base_reading": c_move_in.meter_base_reading,
                "key_delivery_detail": c_move_in.key_delivery_detail,
                "items": [{"item_name": i.item_name, "quantity": i.quantity,
                           "status": i.status, "defect_remark": i.defect_remark}
                          for i in c_move_in_items],
            } if c_move_in else None,
            move_out_inspection={
                "inspection_date": c_move_out.inspection_date,
                "meter_reading": c_move_out.meter_reading,
                "electricity_deduction": c_move_out.electricity_deduction,
                "key_return_status": c_move_out.key_return_status,
                "key_deduction": c_move_out.key_deduction,
                "items": [{"item_name": i.item_name, "quantity": i.quantity,
                           "status": i.status, "deduction_amount": i.deduction_amount}
                          for i in c_move_out_items],
            } if c_move_out else None,
            settlement={
                "deposit_total": c_settlement.deposit_total,
                "electricity_deduction": c_settlement.electricity_deduction,
                "item_damage_deduction": c_settlement.item_damage_deduction,
                "item_missing_deduction": c_settlement.item_missing_deduction,
                "key_deduction": c_settlement.key_deduction,
                "unpaid_bills_total": c_settlement.unpaid_bills_total,
                "other_deduction": c_settlement.other_deduction,
                "actual_refund": c_settlement.actual_refund if c_settlement.actual_refund is not None else round((c_settlement.deposit_total - c_settlement.electricity_deduction
                    - c_settlement.item_damage_deduction - c_settlement.item_missing_deduction
                    - c_settlement.key_deduction - c_settlement.unpaid_bills_total
                    - c_settlement.other_deduction), 2),
                "refund_date": c_settlement.refund_date,
                "refund_method": c_settlement.refund_method,
                "settled_at": c_settlement.settled_at,
            } if c_settlement else None,
            items=[{"item_name": i.item_name, "quantity": i.quantity} for i in c_items],
            payments=[{
                "payment_date": p.payment_date,
                "total_amount": p.total_amount,
                "payment_method": p.payment_method,
                "remark": p.remark,
            } for p in c_payments],
        )
        contract_list.append(item)
        if c.status in ("待交房", "已租", "退租处理中"):
            current_contract = item

    total_days = sum(it.days_rented for it in contract_list)

    return TenantProfileResponse(
        id_number=t.id_number,
        name=t.name,
        phone=t.phone,
        status=t.status,
        archived_at=t.archived_at,
        created_at=t.created_at,
        total_contracts=len(contracts),
        total_days_rented=total_days,
        total_rooms_rented=len(property_ids),
        total_billed=total_billed,
        total_paid=total_paid,
        total_unpaid=round(total_billed - total_paid, 10),
        overdue_count=overdue_count,
        contracts=contract_list,
        current_contract=current_contract,
    ).model_dump()



def restore_tenant(db: Session, id_number: str) -> dict:
    """恢复已退租租客为在用状态。历史合同数据保留，租客以新状态重新开始。"""
    t = get_tenant(db, id_number)
    if t.status != "已退租":
        raise HTTPException(400, f'租客当前状态为"{t.status}"，仅已退租的租客可以恢复')

    t.status = "在用"
    t.archived_at = None
    db.commit()
    db.refresh(t)

    return {
        "id_number": t.id_number,
        "name": t.name,
        "phone": t.phone,
        "status": t.status,
        "archived_at": t.archived_at,
        "message": "租客已恢复为在用状态",
    }

def get_archived_tenants(db: Session, q: str = "") -> list[dict]:
    """列出已退租且归档未超过5个月的租客，支持按姓名/手机号/身份证号搜索。"""
    stmt = select(Tenant).where(
        Tenant.status == "已退租",
        Tenant.archived_at >= _five_months_ago(),
    )
    if q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            Tenant.name.like(pattern),
            Tenant.phone.like(pattern),
            Tenant.id_number.like(pattern),
        ))
    tenants = list(db.scalars(stmt.order_by(Tenant.archived_at.desc())))
    return [{
        "id_number": t.id_number, "name": t.name, "phone": t.phone,
        "status": t.status, "archived_at": t.archived_at,
        "remark": t.remark,
    } for t in tenants]


def cleanup_expired_archives(db: Session) -> dict:
    """清理归档超过5个月的租客及其关联数据。"""
    expired = list(db.scalars(
        select(Tenant).where(
            Tenant.status == "已退租",
            Tenant.archived_at < _five_months_ago(),
        )
    ))
    count = len(expired)
    if not expired:
        return CleanupResponse(removed_count=0, message="没有需要清理的超期归档").model_dump()

    expired_ids = [t.id_number for t in expired]
    contracts = list(db.scalars(
        select(Contract).where(Contract.tenant_id_number.in_(expired_ids))
    ))
    contract_ids = [c.id for c in contracts]

    # 收集将被删除的账单ID
    if contract_ids:
        bill_ids = list(db.scalars(
            select(Bill.id).where(Bill.contract_id.in_(contract_ids))
        ))
        if bill_ids:
            # 只删除与待清理账单关联的 PaymentAllocation（而非整个 Payment）
            # 防止批量收款中 Payment 关联其他在租租客的账单被误删
            allocs_to_delete = list(db.scalars(
                select(PaymentAllocation).where(
                    PaymentAllocation.bill_id.in_(bill_ids)
                )
            ))
            affected_payment_ids = set(a.payment_id for a in allocs_to_delete)
            for a in allocs_to_delete:
                db.delete(a)
            db.flush()
            # 只删除完全没有剩余 allocation 的孤儿 Payment
            for pid in affected_payment_ids:
                remaining = db.scalar(
                    select(func.count(PaymentAllocation.id))
                    .where(PaymentAllocation.payment_id == pid)
                ) or 0
                if remaining == 0:
                    payment = db.get(Payment, pid)
                    if payment:
                        db.delete(payment)

    # 删除合同（CASCADE 清理子表）
    for c in contracts:
        db.delete(c)
    for t in expired:
        db.delete(t)

    db.commit()
    return CleanupResponse(removed_count=count,
                           message=f"已清理 {count} 个超期归档租客及其关联数据").model_dump()
