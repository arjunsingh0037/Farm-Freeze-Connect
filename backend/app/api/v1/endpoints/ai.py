from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, timedelta
import json

from ....core.database import get_db
from ....models import ColdStorage, DailyCapacity, InteractionLog
from ....schemas import (
    TextQueryRequest, QueryResponse, StorageResult,
    AIQueryRequest, AIQueryResponse, StorageSearchResult,
    BookingCreate
)
from ....ai_service import extract_farmer_intent
from ....utils.geo import calculate_distance
from .bookings import create_booking

router = APIRouter()

@router.post("/text-query", response_model=QueryResponse)
def text_query(request: TextQueryRequest, db: Session = Depends(get_db)):
    """Direct text flow: AI extracts intent and searches for cold storage."""
    try:
        # Step 1-2: AI Intent Extraction
        intent = extract_farmer_intent(request.query)
        
        # Log Interaction for Analytics
        interaction = InteractionLog(
            interaction_type="text",
            query_text=request.query,
            extracted_intent=json.dumps(intent),
            location_lat=request.lat,
            location_lng=request.lng
        )
        db.add(interaction)
        db.commit()
        
        # Step 3: Query RDS
        storages = db.query(ColdStorage).all()
        
        # Step 4: Rank and Process
        results = []
        crop = intent.get('crop', '').lower()
        quantity_kg = intent.get('quantity', 0)
        if intent.get('unit') == 'ton':
            quantity_kg *= 1000
            
        for storage in storages:
            distance = calculate_distance(
                request.lat, request.lng, 
                storage.location_lat, storage.location_lng
            )
            
            # Filter within 50km
            if distance > 50.0:
                continue
            
            # Basic filtering for crop support
            supported = storage.supported_crops.lower()
            if supported != 'all' and crop and crop not in supported:
                continue
                
            # Pricing
            price_kg = storage.price_per_kg_per_day
            price_ton = price_kg * 1000
            total_cost = price_kg * quantity_kg
            
            results.append(StorageResult(
                id=str(storage.id),
                name=storage.name,
                address=storage.address,
                distance_km=round(distance, 2),
                price_per_kg=price_kg,
                price_per_ton=price_ton,
                total_cost=round(total_cost, 2),
                available_capacity_kg=storage.total_capacity_kg,
                supported_crops=storage.supported_crops,
                urgency=intent.get('urgency', 'medium'),
                storage_type=intent.get('storage_type', 'short-term')
            ))
        
        results.sort(key=lambda x: x.distance_km)
        return QueryResponse(intent=intent, results=results[:5])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/query", response_model=AIQueryResponse)
def ai_query(request: AIQueryRequest, db: Session = Depends(get_db)):
    """Process natural language query from farmer using AI."""
    try:
        intent = extract_farmer_intent(request.farmer_query)
        
        quantity_kg = intent.get("quantity", 0)
        if intent.get("unit") == "ton":
            quantity_kg *= 1000
        
        time_str = intent.get("time", "today").lower()
        if time_str in ["today", "aaj"]:
            start_date = date.today()
        elif time_str in ["tomorrow", "kal"]:
            start_date = date.today() + timedelta(days=1)
        else:
            start_date = date.today() + timedelta(days=2)
        
        storage_type = intent.get("storage_type", "short-term")
        duration_map = {"short-term": 7, "medium-term": 30, "long-term": 90}
        duration_days = duration_map.get(storage_type, 7)
        
        crop_type = intent.get("crop", "")
        storages = db.query(ColdStorage).all()
        
        available_storages = []
        for storage in storages:
            distance = calculate_distance(
                request.farmer_lat, request.farmer_lng,
                storage.location_lat, storage.location_lng
            )
            
            if distance > 50.0:
                continue
            
            supported_crops = storage.supported_crops.lower()
            if supported_crops != "all" and crop_type:
                if crop_type.lower() not in supported_crops:
                    continue
            
            has_capacity = True
            for i in range(duration_days):
                check_date = start_date + timedelta(days=i)
                daily_record = db.query(DailyCapacity).filter(
                    DailyCapacity.cold_storage_id == storage.id,
                    DailyCapacity.usage_date == check_date
                ).first()
                
                used = daily_record.used_capacity_kg if daily_record else 0.0
                available = storage.total_capacity_kg - used
                
                if available < quantity_kg:
                    has_capacity = False
                    break
            
            if has_capacity:
                total_cost = quantity_kg * storage.price_per_kg_per_day * duration_days
                available_capacity = storage.total_capacity_kg - (daily_record.used_capacity_kg if daily_record else 0.0)
                
                available_storages.append(StorageSearchResult(
                    storage_id=storage.id,
                    storage_name=storage.name,
                    address=storage.address,
                    distance_km=round(distance, 2),
                    price_per_kg_per_day=storage.price_per_kg_per_day,
                    price_per_ton_per_day=storage.price_per_kg_per_day * 1000,
                    total_cost=round(total_cost, 2),
                    available_capacity_kg=available_capacity,
                    supported_crops=storage.supported_crops
                ))
        
        available_storages.sort(key=lambda x: x.distance_km)
        
        booking_suggestion = None
        if available_storages and request.farmer_name and request.farmer_phone:
            closest = available_storages[0]
            booking_suggestion = {
                "cold_storage_id": closest.storage_id,
                "cold_storage_name": closest.storage_name,
                "quantity_kg": quantity_kg,
                "booking_date": str(start_date),
                "duration_days": duration_days,
                "total_cost": closest.total_cost,
                "distance_km": closest.distance_km
            }
        
        return AIQueryResponse(
            intent=intent,
            available_storages=available_storages,
            booking_suggestion=booking_suggestion
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")

@router.post("/book")
def ai_book(request: AIQueryRequest, db: Session = Depends(get_db)):
    """Complete AI-powered booking flow."""
    if not request.farmer_name or not request.farmer_phone:
        raise HTTPException(
            status_code=400,
            detail="farmer_name and farmer_phone are required for booking"
        )
    
    try:
        ai_result = ai_query(request, db)
        if not ai_result.available_storages:
            return {
                "success": False,
                "message": "No available cold storage found matching your requirements",
                "intent": ai_result.intent
            }
        
        closest_storage = ai_result.available_storages[0]
        intent = ai_result.intent
        quantity_kg = intent.get("quantity", 0)
        if intent.get("unit") == "ton":
            quantity_kg *= 1000
        
        time_str = intent.get("time", "today").lower()
        if time_str in ["today", "aaj"]:
            start_date = date.today()
        elif time_str in ["tomorrow", "kal"]:
            start_date = date.today() + timedelta(days=1)
        else:
            start_date = date.today() + timedelta(days=2)
        
        storage_type = intent.get("storage_type", "short-term")
        duration_map = {"short-term": 7, "medium-term": 30, "long-term": 90}
        duration_days = duration_map.get(storage_type, 7)
        
        booking_data = BookingCreate(
            farmer_name=request.farmer_name,
            farmer_phone=request.farmer_phone,
            cold_storage_id=closest_storage.storage_id,
            quantity_kg=quantity_kg,
            booking_date=start_date,
            duration_days=duration_days,
            crop_type=intent.get("crop")
        )
        
        booking = create_booking(booking_data, db)
        
        return {
            "success": True,
            "message": "Booking created successfully",
            "intent": intent,
            "booking": {
                "booking_reference": booking.booking_reference,
                "cold_storage_name": booking.cold_storage_name,
                "quantity_kg": booking.quantity_kg,
                "booking_date": str(booking.booking_date),
                "duration_days": booking.duration_days,
                "total_cost": booking.total_cost,
                "distance_km": closest_storage.distance_km
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"AI booking failed: {str(e)}")
