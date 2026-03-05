from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ....core.database import get_db
from ....models import Farmer
from ....schemas import FarmerCreate, FarmerResponse

router = APIRouter()

@router.post("/", response_model=FarmerResponse)
def create_farmer(farmer: FarmerCreate, db: Session = Depends(get_db)):
    existing = db.query(Farmer).filter(Farmer.phone == farmer.phone).first()
    if existing:
        return existing
    
    db_farmer = Farmer(**farmer.model_dump())
    db.add(db_farmer)
    db.commit()
    db.refresh(db_farmer)
    return db_farmer
