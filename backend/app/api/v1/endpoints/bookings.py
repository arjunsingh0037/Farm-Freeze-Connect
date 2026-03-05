from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import timedelta
import uuid

from ....core.database import get_db
from ....models import Booking, Farmer, ColdStorage, DailyCapacity
from ....schemas import BookingCreate, BookingResponse
from ....notification_service import notification_service

router = APIRouter()

@router.post("/", response_model=BookingResponse)
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
    
    # Send SMS confirmation via Amazon SNS
    try:
        notification_service.send_booking_confirmation(
            farmer_name=farmer.name,
            phone_number=farmer.phone,
            booking_ref=db_booking.booking_reference,
            storage_name=storage.name,
            qty=db_booking.quantity_kg
        )
    except Exception as sns_err:
        print(f"SMS notification failed: {sns_err}")

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

@router.get("/", response_model=List[BookingResponse])
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
