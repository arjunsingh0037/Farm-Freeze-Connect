"""
FarmFreeze Connect - Cold Storage Booking System
"""
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from math import radians, sin, cos, sqrt, atan2
import uuid

# ============ Database Setup ============
DATABASE_URL = "postgresql://postgres:Anjali08*@localhost:5432/farmfreeze"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ============ Models ============
class ColdStorage(Base):
    __tablename__ = "cold_storages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    total_capacity_kg = Column(Float, nullable=False)
    price_per_kg_per_day = Column(Float, nullable=False)
    storage_type = Column(String(50), default="multi-commodity")
    supported_crops = Column(String(500), default="all")  # Comma-separated: "tomato,potato,onion"
    
    bookings = relationship("Booking", back_populates="cold_storage")
    daily_capacity = relationship("DailyCapacity", back_populates="cold_storage")

class Farmer(Base):
    __tablename__ = "farmers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(15), unique=True, nullable=False)
    village = Column(String(255), nullable=True)
    district = Column(String(100), nullable=True)
    
    bookings = relationship("Booking", back_populates="farmer")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(String(20), unique=True, nullable=False)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    cold_storage_id = Column(Integer, ForeignKey("cold_storages.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    booking_date = Column(Date, nullable=False)
    duration_days = Column(Integer, default=1)
    total_cost = Column(Float, nullable=False)
    status = Column(String(20), default="confirmed")
    crop_type = Column(String(100), nullable=True)
    
    farmer = relationship("Farmer", back_populates="bookings")
    cold_storage = relationship("ColdStorage", back_populates="bookings")

class DailyCapacity(Base):
    __tablename__ = "daily_capacity"
    
    id = Column(Integer, primary_key=True, index=True)
    cold_storage_id = Column(Integer, ForeignKey("cold_storages.id"), nullable=False)
    usage_date = Column(Date, nullable=False)
    used_capacity_kg = Column(Float, default=0.0)
    
    cold_storage = relationship("ColdStorage", back_populates="daily_capacity")

# Create tables
Base.metadata.create_all(bind=engine)

# ============ Helper Functions ============
def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two coordinates in km"""
    R = 6371  # Earth's radius in km
    lat1_rad, lat2_rad = radians(lat1), radians(lat2)
    delta_lat = radians(lat2 - lat1)
    delta_lng = radians(lng2 - lng1)
    a = sin(delta_lat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(delta_lng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

# ============ Pydantic Schemas ============
class ColdStorageCreate(BaseModel):
    name: str
    address: str
    location_lat: float
    location_lng: float
    total_capacity_kg: float
    price_per_kg_per_day: float
    storage_type: str = "multi-commodity"
    supported_crops: str = "all"  # Comma-separated: "tomato,potato,onion"

class ColdStorageResponse(BaseModel):
    id: int
    name: str
    address: str
    location_lat: float
    location_lng: float
    total_capacity_kg: float
    price_per_kg_per_day: float
    storage_type: str
    supported_crops: str
    
    class Config:
        from_attributes = True

class FarmerCreate(BaseModel):
    name: str
    phone: str
    village: Optional[str] = None
    district: Optional[str] = None

class FarmerResponse(BaseModel):
    id: int
    name: str
    phone: str
    village: Optional[str]
    district: Optional[str]
    
    class Config:
        from_attributes = True

class BookingCreate(BaseModel):
    farmer_name: str
    farmer_phone: str
    cold_storage_id: int
    quantity_kg: float
    booking_date: date
    duration_days: int = 1
    crop_type: Optional[str] = None

class BookingResponse(BaseModel):
    id: int
    booking_reference: str
    farmer_id: int
    farmer_name: str
    cold_storage_id: int
    cold_storage_name: str
    quantity_kg: float
    booking_date: date
    duration_days: int
    total_cost: float
    status: str
    crop_type: Optional[str]
    
    class Config:
        from_attributes = True

class SearchRequest(BaseModel):
    """Request to search available cold storages"""
    farmer_lat: float
    farmer_lng: float
    crop_type: str
    quantity_kg: float
    start_date: date
    duration_days: int = 1
    max_distance_km: float = 100.0

class StorageSearchResult(BaseModel):
    """Individual storage search result"""
    storage_id: int
    storage_name: str
    address: str
    distance_km: float
    price_per_kg_per_day: float
    total_cost: float
    available_capacity_kg: float
    supported_crops: str
    
    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    """Search API response"""
    count: int
    search_params: dict
    storages: List[StorageSearchResult]

# ============ Dependency ============
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============ API ============
app = FastAPI(title="FarmFreeze Connect API")

@app.get("/")
def root():
    return {"message": "FarmFreeze Connect API", "status": "active"}

# 1. Create Cold Storage
@app.post("/api/cold-storages", response_model=ColdStorageResponse)
def create_cold_storage(storage: ColdStorageCreate, db: Session = Depends(get_db)):
    db_storage = ColdStorage(**storage.model_dump())
    db.add(db_storage)
    db.commit()
    db.refresh(db_storage)
    return db_storage

# 2. Get All Cold Storages
@app.get("/api/cold-storages", response_model=List[ColdStorageResponse])
def get_cold_storages(db: Session = Depends(get_db)):
    return db.query(ColdStorage).all()

# 3. Create Farmer
@app.post("/api/farmers", response_model=FarmerResponse)
def create_farmer(farmer: FarmerCreate, db: Session = Depends(get_db)):
    existing = db.query(Farmer).filter(Farmer.phone == farmer.phone).first()
    if existing:
        return existing
    
    db_farmer = Farmer(**farmer.model_dump())
    db.add(db_farmer)
    db.commit()
    db.refresh(db_farmer)
    return db_farmer

# 4. Create Booking
@app.post("/api/bookings", response_model=BookingResponse)
def create_booking(booking: BookingCreate, db: Session = Depends(get_db)):
    # Find or create farmer
    farmer = db.query(Farmer).filter(Farmer.phone == booking.farmer_phone).first()
    if not farmer:
        farmer = Farmer(name=booking.farmer_name, phone=booking.farmer_phone)
        db.add(farmer)
        db.commit()
        db.refresh(farmer)
    
    # Find cold storage
    storage = db.query(ColdStorage).filter(ColdStorage.id == booking.cold_storage_id).first()
    if not storage:
        raise HTTPException(status_code=404, detail="Cold storage not found")
    
    # Check capacity for each date
    for i in range(booking.duration_days):
        current_date = booking.booking_date + timedelta(days=i)
        
        daily_record = db.query(DailyCapacity).filter(
            DailyCapacity.cold_storage_id == storage.id,
            DailyCapacity.usage_date == current_date
        ).first()
        
        current_used = daily_record.used_capacity_kg if daily_record else 0.0
        new_used = current_used + booking.quantity_kg
        
        if new_used > storage.total_capacity_kg:
            raise HTTPException(
                status_code=400,
                detail=f"Capacity exceeded on {current_date}. Current: {current_used} kg, Requested: {booking.quantity_kg} kg"
            )
    
    # Update daily capacity
    for i in range(booking.duration_days):
        current_date = booking.booking_date + timedelta(days=i)
        
        daily_record = db.query(DailyCapacity).filter(
            DailyCapacity.cold_storage_id == storage.id,
            DailyCapacity.usage_date == current_date
        ).first()
        
        if daily_record:
            daily_record.used_capacity_kg += booking.quantity_kg
        else:
            new_daily = DailyCapacity(
                cold_storage_id=storage.id,
                usage_date=current_date,
                used_capacity_kg=booking.quantity_kg
            )
            db.add(new_daily)
    
    # Create booking
    total_cost = booking.quantity_kg * storage.price_per_kg_per_day * booking.duration_days
    
    db_booking = Booking(
        booking_reference=f"FF-{uuid.uuid4().hex[:8].upper()}",
        farmer_id=farmer.id,
        cold_storage_id=storage.id,
        quantity_kg=booking.quantity_kg,
        booking_date=booking.booking_date,
        duration_days=booking.duration_days,
        total_cost=total_cost,
        crop_type=booking.crop_type
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    
    return BookingResponse(
        id=db_booking.id,
        booking_reference=db_booking.booking_reference,
        farmer_id=farmer.id,
        farmer_name=farmer.name,
        cold_storage_id=storage.id,
        cold_storage_name=storage.name,
        quantity_kg=db_booking.quantity_kg,
        booking_date=db_booking.booking_date,
        duration_days=db_booking.duration_days,
        total_cost=db_booking.total_cost,
        status=db_booking.status,
        crop_type=db_booking.crop_type
    )

# 6. Get All Bookings
@app.get("/api/bookings", response_model=List[BookingResponse])
def get_bookings(db: Session = Depends(get_db)):
    bookings = db.query(Booking).all()
    result = []
    for b in bookings:
        farmer = db.query(Farmer).filter(Farmer.id == b.farmer_id).first()
        storage = db.query(ColdStorage).filter(ColdStorage.id == b.cold_storage_id).first()
        result.append(BookingResponse(
            id=b.id,
            booking_reference=b.booking_reference,
            farmer_id=b.farmer_id,
            farmer_name=farmer.name if farmer else "",
            cold_storage_id=b.cold_storage_id,
            cold_storage_name=storage.name if storage else "",
            quantity_kg=b.quantity_kg,
            booking_date=b.booking_date,
            duration_days=b.duration_days,
            total_cost=b.total_cost,
            status=b.status,
            crop_type=b.crop_type
        ))
    return result

# 7. Get Single Cold Storage
@app.get("/api/cold-storages/{storage_id}", response_model=ColdStorageResponse)
def get_cold_storage(storage_id: int, db: Session = Depends(get_db)):
    storage = db.query(ColdStorage).filter(ColdStorage.id == storage_id).first()
    if not storage:
        raise HTTPException(status_code=404, detail="Cold storage not found")
    return storage

# 8. Check Availability for a Storage
@app.get("/api/cold-storages/{storage_id}/availability")
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)