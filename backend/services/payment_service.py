"""
收款 Service。
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from fastapi import HTTPException

from models.orm import Payment, PaymentAllocation, Bill, Contract
from services.helpers import get_or_404


def create_payment(db: Session, data) -> dict:
    bill = get_or_404(db, Bill, data.bill_id, "账单")
    if bill.status not in ("未付", "部分付"):
        raise HTTPException(400, f"账单状态为\"{bill.status}\"，无法收款")

    # 校验收款金额不超过账单剩余待付
    paid_so_far = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
        .where(PaymentAllocation.bill_id == data.bill_id)
    ) or 0
    remaining = max(0, (bill.total or 0) - paid_so_far)
    if data.amount > remaining:
        raise HTTPException(400, f"收款金额（{data.amount}）超过账单剩余待付金额（{remaining}元）")

    p = Payment(
        payment_date=data.payment_date,
        total_amount=data.amount,
        payment_method=data.payment_method,
        remark=data.remark,
    )
    db.add(p)
    db.flush()

    # 分摊到账单
    db.add(PaymentAllocation(payment_id=p.id, bill_id=data.bill_id, amount=data.amount))
    db.flush()

    # 更新账单状态（必须在 allocation 创建后调用）
    _update_bill_status(db, data.bill_id)

    db.commit()
    db.refresh(p)
    allocs_by_payment, bills_map, contracts_map = _load_payment_context(db, [p])
    return _payment_to_dict(p, allocs_by_payment.get(p.id, []), bills_map, contracts_map)


def create_batch_payment(db: Session, data) -> dict:
    if len(data.bill_ids) < 2:
        raise HTTPException(400, "批量收款至少需要2条账单")

    bills = list(db.scalars(select(Bill).where(Bill.id.in_(data.bill_ids))))
    if len(bills) != len(data.bill_ids):
        raise HTTPException(400, "部分账单不存在")
    unpayable = [b for b in bills if b.status not in ("未付", "部分付")]
    if unpayable:
        raise HTTPException(400, f"以下账单状态不允许收款: {', '.join(b.bill_code for b in unpayable)}")

    # 计算每张账单的剩余待付，防止超付
    remaining_map: dict[int, int] = {}
    for b in bills:
        paid = db.scalar(
            select(func.coalesce(func.sum(PaymentAllocation.amount), 0))
            .where(PaymentAllocation.bill_id == b.id)
        ) or 0
        remaining_map[b.id] = max(0, (b.total or 0) - paid)
    total_remaining = sum(remaining_map.values())
    if data.total_amount > total_remaining:
        raise HTTPException(400, f"总金额（{data.total_amount}）超过所有账单剩余待付合计（{total_remaining}元）")

    p = Payment(
        payment_date=data.payment_date,
        total_amount=data.total_amount,
        payment_method=data.payment_method,
        remark=data.remark,
    )
    db.add(p)
    db.flush()

    # 按剩余待付比例分摊，每张账单不超过其剩余待付
    remaining_amount = data.total_amount
    for i, bill_id in enumerate(data.bill_ids):
        cap = remaining_map[bill_id]
        if i == len(data.bill_ids) - 1:
            # 最后一张账单吸收余额
            amount = min(remaining_amount, cap)
        else:
            # 按比例分摊，不超过该账单剩余待付
            amount = min(
                round(data.total_amount * cap / total_remaining) if total_remaining > 0 else 0,
                cap,
                remaining_amount,
            )
        if amount > 0:
            db.add(PaymentAllocation(payment_id=p.id, bill_id=bill_id, amount=amount))
            remaining_amount -= amount

    db.flush()

    # 更新每张账单的状态（必须在 allocation 创建后调用）
    for bill_id in data.bill_ids:
        _update_bill_status(db, bill_id)

    db.commit()
    db.refresh(p)
    allocs_by_payment, bills_map, contracts_map = _load_payment_context(db, [p])
    return _payment_to_dict(p, allocs_by_payment.get(p.id, []), bills_map, contracts_map)


def _update_bill_status(db: Session, bill_id: int) -> None:
    bill = db.get(Bill, bill_id)
    if not bill:
        return
    db.flush()
    paid = db.scalar(
        select(func.coalesce(func.sum(PaymentAllocation.amount), 0)).where(PaymentAllocation.bill_id == bill_id)
    ) or 0
    if paid >= bill.total:
        bill.status = "已付"
    elif paid > 0:
        bill.status = "部分付"


def _payment_to_dict(p: Payment, allocs: list, bills_map: dict, contracts_map: dict) -> dict:
    alloc_details = []
    for a in allocs:
        b = bills_map.get(a.bill_id)
        ct = contracts_map.get(b.contract_id) if b else None
        alloc_details.append({
            "id": a.id, "bill_id": a.bill_id,
            "bill_code": b.bill_code if b else "",
            "contract_code": ct.contract_code if ct else "",
            "amount": a.amount,
        })
    return {
        "id": p.id, "payment_date": p.payment_date,
        "total_amount": p.total_amount, "payment_method": p.payment_method,
        "remark": p.remark, "created_at": p.created_at,
        "allocations": alloc_details,
    }


def _load_payment_context(db: Session, payments: list) -> tuple[dict, dict, dict]:
    """Batch load allocations, bills, contracts for a list of payments."""
    payment_ids = [p.id for p in payments]
    all_allocs = list(db.scalars(
        select(PaymentAllocation).where(PaymentAllocation.payment_id.in_(payment_ids))
    ))
    allocs_by_payment: dict[int, list] = {}
    bill_ids = set()
    for a in all_allocs:
        allocs_by_payment.setdefault(a.payment_id, []).append(a)
        bill_ids.add(a.bill_id)
    bills_map = {b.id: b for b in db.scalars(select(Bill).where(Bill.id.in_(list(bill_ids))))}
    contract_ids = {b.contract_id for b in bills_map.values()}
    contracts_map = {c.id: c for c in db.scalars(select(Contract).where(Contract.id.in_(list(contract_ids))))}
    return allocs_by_payment, bills_map, contracts_map


def list_payments(db: Session) -> list[dict]:
    payments = list(db.scalars(select(Payment).order_by(Payment.payment_date.desc())))
    if not payments:
        return []
    allocs_by_payment, bills_map, contracts_map = _load_payment_context(db, payments)
    return [_payment_to_dict(p, allocs_by_payment.get(p.id, []), bills_map, contracts_map) for p in payments]


def get_payment(db: Session, payment_id: int) -> dict:
    p = get_or_404(db, Payment, payment_id, "收款记录")
    allocs_by_payment, bills_map, contracts_map = _load_payment_context(db, [p])
    return _payment_to_dict(p, allocs_by_payment.get(p.id, []), bills_map, contracts_map)
