"""
结算单 API。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import SettlementCreate, SettlementConfirm
from services.settlement_service import create_settlement, get_settlement, confirm_settlement

router = APIRouter()


@router.get("/{contract_id}")
def _get(contract_id: int, db: Session = Depends(get_db)):
    return get_settlement(db, contract_id)


@router.post("/{contract_id}")
def _create(contract_id: int, data: SettlementCreate, db: Session = Depends(get_db)):
    return create_settlement(db, contract_id, data)


@router.post("/{contract_id}/confirm")
def _confirm(contract_id: int, data: SettlementConfirm, db: Session = Depends(get_db)):
    return confirm_settlement(db, contract_id, data)
