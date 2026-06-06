"""
合同管理 API — 路由层。
"""
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import (
    ContractCreate, ContractUpdate, ContractResponse,
    ContractItemIn, MessageResponse,
)
from services.contract_service import (
    list_contracts, get_contract, create_contract, update_contract,
    add_item, delete_item, cancel_contract, start_termination, cancel_termination,
    upload_image, delete_image,
)

router = APIRouter()


@router.get("", response_model=list[ContractResponse])
def _list(status: str | None = None, db: Session = Depends(get_db)):
    return list_contracts(db, status)


@router.get("/{contract_id}", response_model=ContractResponse)
def _get(contract_id: int, db: Session = Depends(get_db)):
    return get_contract(db, contract_id)


@router.post("", response_model=ContractResponse, status_code=201)
def _create(data: ContractCreate, db: Session = Depends(get_db)):
    return create_contract(db, data)


@router.put("/{contract_id}", response_model=ContractResponse)
def _update(contract_id: int, data: ContractUpdate, db: Session = Depends(get_db)):
    return update_contract(db, contract_id, data)


@router.post("/{contract_id}/items", response_model=ContractResponse)
def _add_item(contract_id: int, item: ContractItemIn, db: Session = Depends(get_db)):
    return add_item(db, contract_id, item)


@router.delete("/{contract_id}/items/{item_id}", response_model=ContractResponse)
def _delete_item(contract_id: int, item_id: int, db: Session = Depends(get_db)):
    return delete_item(db, contract_id, item_id)


@router.post("/{contract_id}/images", response_model=ContractResponse)
def _upload_image(contract_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return upload_image(db, contract_id, file)


@router.delete("/{contract_id}/images/{image_id}", response_model=ContractResponse)
def _delete_image(contract_id: int, image_id: int, db: Session = Depends(get_db)):
    return delete_image(db, contract_id, image_id)


@router.post("/{contract_id}/cancel", response_model=MessageResponse)
def _cancel(contract_id: int, db: Session = Depends(get_db)):
    return {"message": cancel_contract(db, contract_id)}


@router.post("/{contract_id}/start-termination", response_model=MessageResponse)
def _start_termination(contract_id: int, db: Session = Depends(get_db)):
    return {"message": start_termination(db, contract_id)}


@router.post("/{contract_id}/cancel-termination", response_model=MessageResponse)
def _cancel_termination(contract_id: int, db: Session = Depends(get_db)):
    return {"message": cancel_termination(db, contract_id)}
