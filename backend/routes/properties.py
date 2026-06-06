"""
房产管理 API — 路由层。
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import PropertyCreate, PropertyUpdate, PropertyResponse, MessageResponse
from services.property_service import list_properties, get_property, create_property, update_property, delete_property

router = APIRouter()


@router.get("", response_model=list[PropertyResponse])
def _list(status: str | None = None, db: Session = Depends(get_db)):
    return list_properties(db, status)


@router.get("/{property_id}", response_model=PropertyResponse)
def _get(property_id: int, db: Session = Depends(get_db)):
    return get_property(db, property_id)


@router.post("", response_model=PropertyResponse, status_code=201)
def _create(data: PropertyCreate, db: Session = Depends(get_db)):
    return create_property(db, data)


@router.put("/{property_id}", response_model=PropertyResponse)
def _update(property_id: int, data: PropertyUpdate, db: Session = Depends(get_db)):
    return update_property(db, property_id, data)


@router.delete("/{property_id}", response_model=MessageResponse)
def _delete(property_id: int, db: Session = Depends(get_db)):
    delete_property(db, property_id)
    return {"message": "删除成功"}
