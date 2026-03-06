from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date, timedelta

from ....core.database import get_db
from ....models import ColdStorage, DailyCapacity
from ....schemas import ColdStorageCreate, ColdStorageResponse

router = APIRouter()

@router.post("/", response_model=ColdStorageResponse)
def create_cold_storage(storage: ColdStorageCreate, db: Session = Depends(get_db)):
    db_storage = ColdStorage(**storage.model_dump())
    db.add(db_storage)
    db.commit()
    db.refresh(db_storage)
    return db_storage

@router.get("/", response_model=List[ColdStorageResponse])
def get_cold_storages(db: Session = Depends(get_db)):
    return db.query(ColdStorage).all()

@router.get("/{storage_id}", response_model=ColdStorageResponse)
def get_cold_storage(storage_id: int, db: Session = Depends(get_db)):
    storage = db.query(ColdStorage).filter(ColdStorage.id == storage_id).first()
    if not storage:
        raise HTTPException(status_code=404, detail="Cold storage not found")
    return storage

@router.get("/{storage_id}/availability")
def check_availability(
    storage_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db)
):
    storage = db.query(ColdStorage).filter(ColdStorage.id == storage_id).first()
    if not storage:
        raise HTTPException(status_code=404, detail="Cold storage not found")
    
    availability = []
    current = start_date
    while current <= end_date:
        daily_record = db.query(DailyCapacity).filter(
            DailyCapacity.cold_storage_id == storage_id,
            DailyCapacity.usage_date == current
        ).first()
        
        used = daily_record.used_capacity_kg if daily_record else 0.0
        available = storage.total_capacity_kg - used
        
        availability.append({
            "date": str(current),
            "used_kg": used,
            "available_kg": available,
            "total_kg": storage.total_capacity_kg
        })
        current += timedelta(days=1)
    
    return {
        "storage_id": storage_id,
        "storage_name": storage.name,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "availability": availability
    }
