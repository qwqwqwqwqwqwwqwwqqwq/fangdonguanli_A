"""
验收管理 API — 交房验收 + 退房验收。
"""
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import MoveInInspectionCreate, MoveInInspectionItemUpdate, MoveOutInspectionCreate, MoveOutInspectionUpdate, MoveOutInspectionItemUpdate, MoveOutKeyDeductionUpdate
from services.inspection_service import (
    create_move_in_inspection, get_move_in_inspection,
    update_move_in_item, upload_move_in_image, upload_move_in_signature,
    create_move_out_inspection, get_move_out_inspection,
    update_move_out_item, update_move_out_key_deduction, update_move_out_inspection, upload_move_out_image,
)

router = APIRouter()


# 交房验收
@router.post("/move-in")
def _create_move_in(data: MoveInInspectionCreate, db: Session = Depends(get_db)):
    return create_move_in_inspection(db, data)


@router.get("/move-in/{contract_id}")
def _get_move_in(contract_id: int, db: Session = Depends(get_db)):
    return get_move_in_inspection(db, contract_id)


@router.put("/move-in/{inspection_id}/items/{item_id}")
def _update_move_in_item(inspection_id: int, item_id: int, data: MoveInInspectionItemUpdate, db: Session = Depends(get_db)):
    return update_move_in_item(db, inspection_id, item_id, data)


@router.post("/move-in/{inspection_id}/images")
def _upload_move_in_image(inspection_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return upload_move_in_image(db, inspection_id, file)


@router.post("/move-in/{inspection_id}/signatures/{role}")
def _upload_move_in_signature(inspection_id: int, role: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    if role not in ("landlord", "tenant"):
        raise HTTPException(400, "角色参数必须为 landlord 或 tenant")
    return upload_move_in_signature(db, inspection_id, role, file)


# 退房验收
@router.post("/move-out")
def _create_move_out(data: MoveOutInspectionCreate, db: Session = Depends(get_db)):
    return create_move_out_inspection(db, data)


@router.get("/move-out/{contract_id}")
def _get_move_out(contract_id: int, db: Session = Depends(get_db)):
    return get_move_out_inspection(db, contract_id)


@router.put("/move-out/{inspection_id}/items/{item_id}")
def _update_move_out_item(inspection_id: int, item_id: int, data: MoveOutInspectionItemUpdate, db: Session = Depends(get_db)):
    return update_move_out_item(db, inspection_id, item_id, data)



@router.put("/move-out/{inspection_id}")
def _update_move_out(inspection_id: int, data: MoveOutInspectionUpdate, db: Session = Depends(get_db)):
    return update_move_out_inspection(db, inspection_id, data)


@router.put("/move-out/{inspection_id}/key-deduction")
def _update_move_out_key_deduction(inspection_id: int, data: MoveOutKeyDeductionUpdate, db: Session = Depends(get_db)):
    return update_move_out_key_deduction(db, inspection_id, data)


@router.post("/move-out/{inspection_id}/images")
def _upload_move_out_image(inspection_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return upload_move_out_image(db, inspection_id, file)
