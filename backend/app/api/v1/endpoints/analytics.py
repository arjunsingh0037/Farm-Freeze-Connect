from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import json

from ....core.database import get_db
from ....models import InteractionLog, Booking

router = APIRouter()

@router.get("/demand")
def get_demand_trends(db: Session = Depends(get_db)):
    """Analyze demand trends from interaction logs."""
    interactions = db.query(InteractionLog).all()
    trends = {}
    for log in interactions:
        try:
            intent = json.loads(log.extracted_intent)
            crop = intent.get("crop", "unknown")
            trends[crop] = trends.get(crop, 0) + 1
        except:
            continue
    return {"crop_demand": trends}

@router.get("/utilization")
def get_utilization_patterns(db: Session = Depends(get_db)):
    """Analyze utilization patterns from bookings."""
    bookings = db.query(Booking).all()
    utilization = {}
    for b in bookings:
        storage_id = b.cold_storage_id
        utilization[storage_id] = utilization.get(storage_id, 0) + b.quantity_kg
    return {"storage_utilization_total": utilization}
