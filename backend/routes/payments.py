"""
收款管理 API。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import PaymentCreate, BatchPaymentCreate
from services.payment_service import create_payment, create_batch_payment, list_payments, get_payment

router = APIRouter()


@router.get("")
def _list(db: Session = Depends(get_db)):
    return list_payments(db)


@router.get("/{payment_id}")
def _get(payment_id: int, db: Session = Depends(get_db)):
    return get_payment(db, payment_id)


@router.post("/single")
def _create_single(data: PaymentCreate, db: Session = Depends(get_db)):
    return create_payment(db, data)


@router.post("/batch")
def _create_batch(data: BatchPaymentCreate, db: Session = Depends(get_db)):
    return create_batch_payment(db, data)
