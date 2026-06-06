"""
账单管理 API。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import BillGenerateRequest, BillOtherFeeCreate, DunningCreate
from services.bill_service import generate_bill, list_bills, get_bill, add_other_fee, get_bill_payments, send_dunning, auto_generate_bills

router = APIRouter()


@router.get("")
def _list(contract_id: int | None = None, contract_ids: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    ids_list = None
    if contract_ids:
        ids_list = [int(x) for x in contract_ids.split(",") if x.strip().isdigit()]
    return list_bills(db, contract_id, ids_list, status)


@router.post("/auto-generate")
def _auto_generate(contract_id: int | None = None, db: Session = Depends(get_db)):
    """自动为活跃合同生成缺失月份的账单。"""
    return auto_generate_bills(db, contract_id)


@router.get("/{bill_id}")
def _get(bill_id: int, db: Session = Depends(get_db)):
    return get_bill(db, bill_id)


@router.post("/generate/{contract_id}")
def _generate(contract_id: int, data: BillGenerateRequest, db: Session = Depends(get_db)):
    return generate_bill(db, contract_id, data)


@router.get("/{bill_id}/payments")
def _get_payments(bill_id: int, db: Session = Depends(get_db)):
    return get_bill_payments(db, bill_id)


@router.post("/{bill_id}/other-fees")
def _add_other_fee(bill_id: int, data: BillOtherFeeCreate, db: Session = Depends(get_db)):
    return add_other_fee(db, bill_id, data)


@router.post("/{bill_id}/dunning")
def _send_dunning(bill_id: int, data: DunningCreate, db: Session = Depends(get_db)):
    return send_dunning(db, bill_id, data)
