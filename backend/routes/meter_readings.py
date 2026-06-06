"""
电表记录 API。
"""
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import MeterReadingCreate, MeterReadingUpdate
from services.meter_service import list_readings, get_reading, create_reading, update_reading, upload_meter_photo

router = APIRouter()


@router.get("/contracts/{contract_id}/readings")
def _list(contract_id: int, db: Session = Depends(get_db)):
    return list_readings(db, contract_id)


@router.get("/readings/{reading_id}")
def _get(reading_id: int, db: Session = Depends(get_db)):
    return get_reading(db, reading_id)


@router.post("/readings")
def _create(data: MeterReadingCreate, db: Session = Depends(get_db)):
    return create_reading(db, data)


@router.put("/readings/{reading_id}")
def _update(reading_id: int, data: MeterReadingUpdate, db: Session = Depends(get_db)):
    return update_reading(db, reading_id, data)


@router.post("/readings/{reading_id}/photo")
def _upload_photo(reading_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    return upload_meter_photo(db, reading_id, file)
