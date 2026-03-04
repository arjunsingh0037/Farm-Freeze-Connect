"""
FarmFreeze Connect - Cold Storage Booking System
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, timedelta
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
from math import radians, sin, cos, sqrt, atan2
import uuid
from .ai_service import extract_farmer_intent
from .voice_service import voice_service
# ============ Database Setup ============
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./farmfreeze.db")

# SQLite requires check_same_thread=False
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
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

class AIQueryRequest(BaseModel):
    """Request for AI-powered natural language query"""
    farmer_query: str
    farmer_lat: float
    farmer_lng: float
    farmer_name: Optional[str] = None
    farmer_phone: Optional[str] = None

class AIQueryResponse(BaseModel):
    """Response from AI-powered query"""
    intent: dict
    available_storages: List[StorageSearchResult]
    booking_suggestion: Optional[dict] = None

class VoiceQueryRequest(BaseModel):
    """Request for voice-powered query"""
    farmer_lat: float
    farmer_lng: float
    farmer_name: Optional[str] = None
    farmer_phone: Optional[str] = None
    language_code: str = "hi-IN"  # Default to Hindi

class VoiceTranscriptionResponse(BaseModel):
    """Response from voice transcription"""
    transcript: str
    confidence: float
    alternatives: List[str]
    language_detected: str
    processing_time_ms: int

class VoiceRecommendationResponse(BaseModel):
    """Response with voice recommendation for missing fields"""
    missing_fields: List[str]
    recommendation_text: str
    audio_available: bool
    language_detected: str
    processing_time_ms: int

class SmartVoiceBookingResponse(BaseModel):
    """Enhanced voice booking response with recommendations"""
    transcription: VoiceTranscriptionResponse
    intent: dict
    missing_fields: List[str]
    recommendation: Optional[VoiceRecommendationResponse] = None
    available_storages: List[StorageSearchResult]
    booking: Optional[dict] = None
    success: bool
    message: str
    requires_more_info: bool

class VoiceBookingResponse(BaseModel):
    """Response from voice booking"""
    transcription: VoiceTranscriptionResponse
    intent: dict
    available_storages: List[StorageSearchResult]
    booking: Optional[dict] = None
    success: bool
    message: str

class VoiceStorageResponse(BaseModel):
    """Response for voice input storage"""
    stored: bool
    s3_key: str
    s3_uri: str
    bucket: str
    size_bytes: int
    timestamp: str
    mock: bool

class StoredVoiceInput(BaseModel):
    """Stored voice input metadata"""
    s3_key: str
    s3_uri: str
    size: int
    last_modified: str
    farmer_name: str
    farmer_phone: str
    language_code: str
    upload_timestamp: str
    mock: bool

class VoiceInputListResponse(BaseModel):
    """Response for listing stored voice inputs"""
    voice_inputs: List[StoredVoiceInput]
    total_count: int
    bucket: str

class EnhancedVoiceBookingResponse(BaseModel):
    """Enhanced voice booking response with S3 storage info"""
    transcription: VoiceTranscriptionResponse
    intent: dict
    missing_fields: List[str]
    recommendation: Optional[VoiceRecommendationResponse] = None
    available_storages: List[StorageSearchResult]
    booking: Optional[dict] = None
    voice_storage: Optional[VoiceStorageResponse] = None
    success: bool
    message: str
    requires_more_info: bool

class EnhancedVoiceBookingResponse(BaseModel):
    """Enhanced voice booking response with S3 storage info"""
    transcription: VoiceTranscriptionResponse
    intent: dict
    missing_fields: List[str]
    recommendation: Optional[VoiceRecommendationResponse] = None
    available_storages: List[StorageSearchResult]
    booking: Optional[dict] = None
    voice_storage: Optional[VoiceStorageResponse] = None
    success: bool
    message: str
    requires_more_info: bool

    class VoiceRecommendationResponse(BaseModel):
        """Response with voice recommendation for missing fields"""
        missing_fields: List[str]
        recommendation_text: str
        audio_available: bool
        language_detected: str
        processing_time_ms: int

    class SmartVoiceBookingResponse(BaseModel):
        """Enhanced voice booking response with recommendations"""
        transcription: VoiceTranscriptionResponse
        intent: dict
        missing_fields: List[str]
        recommendation: Optional[VoiceRecommendationResponse] = None
        available_storages: List[StorageSearchResult]
        booking: Optional[dict] = None
        success: bool
        message: str
        requires_more_info: bool

    class VoiceBookingResponse(BaseModel):
        """Response from voice booking"""
        transcription: VoiceTranscriptionResponse
        intent: dict
        available_storages: List[StorageSearchResult]
        booking: Optional[dict] = None
        success: bool
        message: str

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

# 9. AI-Powered Natural Language Query
@app.post("/api/ai/query", response_model=AIQueryResponse)
def ai_query(request: AIQueryRequest, db: Session = Depends(get_db)):
    """
    Process natural language query from farmer using AI
    Extract intent and search for available cold storage
    """
    try:
        # Extract intent using AI
        intent = extract_farmer_intent(request.farmer_query)
        
        # Convert quantity to kg if needed
        quantity_kg = intent.get("quantity", 0)
        if intent.get("unit") == "ton":
            quantity_kg = quantity_kg * 1000
        
        # Determine start date based on time field
        time_str = intent.get("time", "today").lower()
        if time_str in ["today", "aaj"]:
            start_date = date.today()
        elif time_str in ["tomorrow", "kal"]:
            start_date = date.today() + timedelta(days=1)
        else:
            start_date = date.today() + timedelta(days=2)
        
        # Determine duration based on storage type
        storage_type = intent.get("storage_type", "short-term")
        duration_map = {
            "short-term": 7,
            "medium-term": 30,
            "long-term": 90
        }
        duration_days = duration_map.get(storage_type, 7)
        
        # Search for available cold storages
        crop_type = intent.get("crop", "")
        storages = db.query(ColdStorage).all()
        
        available_storages = []
        for storage in storages:
            # Calculate distance
            distance = calculate_distance(
                request.farmer_lat,
                request.farmer_lng,
                storage.location_lat,
                storage.location_lng
            )
            
            # Check if crop is supported
            supported_crops = storage.supported_crops.lower()
            if supported_crops != "all" and crop_type:
                if crop_type.lower() not in supported_crops:
                    continue
            
            # Check capacity for the duration
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
                    total_cost=round(total_cost, 2),
                    available_capacity_kg=available_capacity,
                    supported_crops=storage.supported_crops
                ))
        
        # Sort by distance
        available_storages.sort(key=lambda x: x.distance_km)
        
        # Create booking suggestion for the closest storage
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI query failed: {str(e)}")

# 10. AI-Powered Booking (Complete Flow)
@app.post("/api/ai/book")
def ai_book(request: AIQueryRequest, db: Session = Depends(get_db)):
    """
    Complete AI-powered booking flow:
    1. Extract intent from natural language
    2. Search for available storage
    3. Create booking automatically
    """
    if not request.farmer_name or not request.farmer_phone:
        raise HTTPException(
            status_code=400,
            detail="farmer_name and farmer_phone are required for booking"
        )
    
    try:
        # Get AI query results
        ai_result = ai_query(request, db)
        
        if not ai_result.available_storages:
            return {
                "success": False,
                "message": "No available cold storage found matching your requirements",
                "intent": ai_result.intent
            }
        
        # Use the closest storage
        closest_storage = ai_result.available_storages[0]
        
        # Extract booking details from intent
        intent = ai_result.intent
        quantity_kg = intent.get("quantity", 0)
        if intent.get("unit") == "ton":
            quantity_kg = quantity_kg * 1000
        
        time_str = intent.get("time", "today").lower()
        if time_str in ["today", "aaj"]:
            start_date = date.today()
        elif time_str in ["tomorrow", "kal"]:
            start_date = date.today() + timedelta(days=1)
        else:
            start_date = date.today() + timedelta(days=2)
        
        storage_type = intent.get("storage_type", "short-term")
        duration_map = {
            "short-term": 7,
            "medium-term": 30,
            "long-term": 90
        }
        duration_days = duration_map.get(storage_type, 7)
        
        # Create booking
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI booking failed: {str(e)}")
# 11. Voice Transcription Endpoint
@app.post("/api/voice/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_voice(
    audio_file: UploadFile = File(...),
    language_code: str = "hi-IN"
):
    """
    Transcribe voice input to text using Amazon Transcribe
    Supports Hindi (hi-IN) and Indian English (en-IN)
    """
    import time
    start_time = time.time()
    
    # Validate file type
    if not audio_file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400,
            detail="File must be an audio file"
        )
    
    try:
        # Read audio file content
        audio_content = await audio_file.read()
        
        # Transcribe using voice service
        result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return VoiceTranscriptionResponse(
            transcript=result['transcript'],
            confidence=result['confidence'],
            alternatives=result.get('alternatives', []),
            language_detected=language_code,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice transcription failed: {str(e)}"
        )

# 12. Voice Query Endpoint (Voice to Storage Search)
@app.post("/api/voice/query")
async def voice_query(
    audio_file: UploadFile = File(...),
    farmer_lat: float = 28.6139,
    farmer_lng: float = 77.2090,
    farmer_name: Optional[str] = None,
    farmer_phone: Optional[str] = None,
    language_code: str = "hi-IN",
    db: Session = Depends(get_db)
):
    """
    Complete voice-to-storage-search workflow:
    1. Transcribe voice to text
    2. Extract intent using AI
    3. Search for available storage
    """
    try:
        # Step 1: Transcribe voice
        audio_content = await audio_file.read()
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            raise HTTPException(
                status_code=500,
                detail="Voice transcription failed"
            )
        
        farmer_query = transcription_result['transcript']
        
        # Step 2: Process with AI (reuse existing logic)
        ai_request = AIQueryRequest(
            farmer_query=farmer_query,
            farmer_lat=farmer_lat,
            farmer_lng=farmer_lng,
            farmer_name=farmer_name,
            farmer_phone=farmer_phone
        )
        
        ai_result = ai_query(ai_request, db)
        
        # Step 3: Return combined result
        return {
            "transcription": {
                "transcript": transcription_result['transcript'],
                "confidence": transcription_result['confidence'],
                "alternatives": transcription_result.get('alternatives', []),
                "language_detected": language_code,
                "processing_time_ms": 0  # Will be calculated in frontend
            },
            "intent": ai_result.intent,
            "available_storages": ai_result.available_storages,
            "booking_suggestion": ai_result.booking_suggestion
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice query processing failed: {str(e)}"
        )

# 13. Voice Booking Endpoint (Complete Voice-to-Booking)
@app.post("/api/voice/book", response_model=VoiceBookingResponse)
async def voice_book(
    audio_file: UploadFile = File(...),
    farmer_lat: float = 28.6139,
    farmer_lng: float = 77.2090,
    farmer_name: str = "Unknown Farmer",
    farmer_phone: str = "+919999999999",
    language_code: str = "hi-IN",
    db: Session = Depends(get_db)
):
    """
    Complete voice-to-booking workflow:
    1. Transcribe voice to text
    2. Extract intent using AI
    3. Search for available storage
    4. Create booking automatically
    """
    import time
    start_time = time.time()
    
    try:
        # Step 1: Transcribe voice
        audio_content = await audio_file.read()
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            return VoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript="",
                    confidence=0.0,
                    alternatives=[],
                    language_detected=language_code,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ),
                intent={},
                available_storages=[],
                booking=None,
                success=False,
                message="Voice transcription failed"
            )
        
        farmer_query = transcription_result['transcript']
        
        # Step 2: Process with AI booking (reuse existing logic)
        ai_request = AIQueryRequest(
            farmer_query=farmer_query,
            farmer_lat=farmer_lat,
            farmer_lng=farmer_lng,
            farmer_name=farmer_name,
            farmer_phone=farmer_phone
        )
        
        # Use existing AI booking logic
        booking_result = ai_book(ai_request, db)
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return VoiceBookingResponse(
            transcription=VoiceTranscriptionResponse(
                transcript=transcription_result['transcript'],
                confidence=transcription_result['confidence'],
                alternatives=transcription_result.get('alternatives', []),
                language_detected=language_code,
                processing_time_ms=processing_time
            ),
            intent=booking_result.get('intent', {}),
            available_storages=[],  # Not included in booking response
            booking=booking_result.get('booking'),
            success=booking_result.get('success', False),
            message=booking_result.get('message', '')
        )
        
    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        
        return VoiceBookingResponse(
            transcription=VoiceTranscriptionResponse(
                transcript="",
                confidence=0.0,
                alternatives=[],
                language_detected=language_code,
                processing_time_ms=processing_time
            ),
            intent={},
            available_storages=[],
            booking=None,
            success=False,
            message=f"Voice booking failed: {str(e)}"
        )

# 14. Voice Test Endpoint (For Development)
@app.post("/api/voice/test")
async def test_voice_service():
    """
    Test endpoint to verify voice service configuration
    """
    try:
        # Test with mock data
        mock_audio_path = "test_audio.wav"
        result = voice_service._get_mock_transcription(mock_audio_path)
        
        return {
            "voice_service_status": "operational",
            "aws_transcribe_configured": voice_service.transcribe_client is not None,
            "s3_configured": voice_service.s3_client is not None,
            "mock_transcription": result,
            "supported_languages": ["hi-IN", "en-IN", "en-US"],
            "message": "Voice service is ready. Upload audio files to /api/voice/transcribe"
        }
        
    except Exception as e:
        return {
            "voice_service_status": "error",
            "error": str(e),
            "message": "Voice service configuration needs attention"
        }

# 15. Smart Voice Booking with Recommendations
@app.post("/api/voice/smart-book", response_model=SmartVoiceBookingResponse)
async def smart_voice_book(
    audio_file: UploadFile = File(...),
    farmer_lat: float = 28.6139,
    farmer_lng: float = 77.2090,
    farmer_name: str = "Unknown Farmer",
    farmer_phone: str = "+919999999999",
    language_code: str = "hi-IN",
    db: Session = Depends(get_db)
):
    """
    Smart voice booking with missing field detection and voice recommendations:
    1. Transcribe voice to text
    2. Extract intent using AI
    3. Detect missing required fields
    4. Generate voice recommendations for missing fields
    5. If all fields present, proceed with booking
    """
    import time
    start_time = time.time()
    
    try:
        # Step 1: Transcribe voice
        audio_content = await audio_file.read()
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            return SmartVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript="",
                    confidence=0.0,
                    alternatives=[],
                    language_detected=language_code,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ),
                intent={},
                missing_fields=["transcription_failed"],
                recommendation=None,
                available_storages=[],
                booking=None,
                success=False,
                message="Voice transcription failed",
                requires_more_info=True
            )
        
        farmer_query = transcription_result['transcript']
        
        # Step 2: Extract intent using AI
        intent = extract_farmer_intent(farmer_query)
        
        # Step 3: Check for missing required fields
        required_fields = ["crop", "quantity"]
        missing_fields = []
        
        if not intent.get("crop") or intent.get("crop") == "unknown":
            missing_fields.append("crop")
        if not intent.get("quantity") or intent.get("quantity") == 0:
            missing_fields.append("quantity")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Step 4: If fields are missing, generate voice recommendation
        if missing_fields:
            recommendation_text = voice_service.generate_missing_field_prompt(missing_fields, language_code)
            
            return SmartVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript=transcription_result['transcript'],
                    confidence=transcription_result['confidence'],
                    alternatives=transcription_result.get('alternatives', []),
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                intent=intent,
                missing_fields=missing_fields,
                recommendation=VoiceRecommendationResponse(
                    missing_fields=missing_fields,
                    recommendation_text=recommendation_text,
                    audio_available=True,
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                available_storages=[],
                booking=None,
                success=False,
                message=f"Missing required information: {', '.join(missing_fields)}",
                requires_more_info=True
            )
        
        # Step 5: All fields present, proceed with booking
        ai_request = AIQueryRequest(
            farmer_query=farmer_query,
            farmer_lat=farmer_lat,
            farmer_lng=farmer_lng,
            farmer_name=farmer_name,
            farmer_phone=farmer_phone
        )
        
        # Search for available storage
        search_result = ai_query(ai_request, db)
        
        if not search_result.available_storages:
            return SmartVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript=transcription_result['transcript'],
                    confidence=transcription_result['confidence'],
                    alternatives=transcription_result.get('alternatives', []),
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                intent=intent,
                missing_fields=[],
                recommendation=None,
                available_storages=[],
                booking=None,
                success=False,
                message="No available cold storage found matching your requirements",
                requires_more_info=False
            )
        
        # Create booking
        booking_result = ai_book(ai_request, db)
        
        return SmartVoiceBookingResponse(
            transcription=VoiceTranscriptionResponse(
                transcript=transcription_result['transcript'],
                confidence=transcription_result['confidence'],
                alternatives=transcription_result.get('alternatives', []),
                language_detected=language_code,
                processing_time_ms=processing_time
            ),
            intent=intent,
            missing_fields=[],
            recommendation=None,
            available_storages=search_result.available_storages,
            booking=booking_result.get('booking'),
            success=booking_result.get('success', False),
            message=booking_result.get('message', ''),
            requires_more_info=False
        )
        
    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        
        return SmartVoiceBookingResponse(
            transcription=VoiceTranscriptionResponse(
                transcript="",
                confidence=0.0,
                alternatives=[],
                language_detected=language_code,
                processing_time_ms=processing_time
            ),
            intent={},
            missing_fields=["system_error"],
            recommendation=None,
            available_storages=[],
            booking=None,
            success=False,
            message=f"Smart voice booking failed: {str(e)}",
            requires_more_info=True
        )

# 16. Generate Voice Recommendation Audio
@app.post("/api/voice/recommendation-audio")
async def get_recommendation_audio(
    missing_fields: List[str],
    language_code: str = "hi-IN"
):
    """
    Generate voice recommendation audio for missing fields
    """
    try:
        recommendation_text = voice_service.generate_missing_field_prompt(missing_fields, language_code)
        audio_bytes = voice_service.generate_voice_recommendation(recommendation_text, language_code)
        
        from fastapi.responses import Response
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=recommendation.mp3",
                "X-Recommendation-Text": recommendation_text
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice recommendation generation failed: {str(e)}"
        )
# 17. Enhanced Voice Booking with S3 Storage
@app.post("/api/voice/enhanced-book", response_model=EnhancedVoiceBookingResponse)
async def enhanced_voice_book(
    audio_file: UploadFile = File(...),
    farmer_lat: float = 28.6139,
    farmer_lng: float = 77.2090,
    farmer_name: str = "Unknown Farmer",
    farmer_phone: str = "+919999999999",
    language_code: str = "hi-IN",
    store_in_s3: bool = True,
    db: Session = Depends(get_db)
):
    """
    Enhanced voice booking with S3 storage:
    1. Store voice input in S3 bucket
    2. Transcribe voice to text
    3. Extract intent using AI
    4. Detect missing required fields
    5. Generate voice recommendations for missing fields
    6. If all fields present, proceed with booking
    """
    import time
    start_time = time.time()
    
    try:
        # Step 1: Read audio content
        audio_content = await audio_file.read()
        
        # Step 2: Store voice input in S3 (if enabled)
        voice_storage_info = None
        if store_in_s3:
            farmer_info = {
                'name': farmer_name,
                'phone': farmer_phone
            }
            storage_result = voice_service.store_voice_input_s3(audio_content, farmer_info, language_code)
            voice_storage_info = VoiceStorageResponse(**storage_result)
        
        # Step 3: Transcribe voice
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            return EnhancedVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript="",
                    confidence=0.0,
                    alternatives=[],
                    language_detected=language_code,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ),
                intent={},
                missing_fields=["transcription_failed"],
                recommendation=None,
                available_storages=[],
                booking=None,
                voice_storage=voice_storage_info,
                success=False,
                message="Voice transcription failed",
                requires_more_info=True
            )
        
        farmer_query = transcription_result['transcript']
        
        # Step 4: Extract intent using AI
        intent = extract_farmer_intent(farmer_query)
        
        # Step 5: Check for missing required fields
        required_fields = ["crop", "quantity"]
        missing_fields = []
        
        if not intent.get("crop") or intent.get("crop") == "unknown":
            missing_fields.append("crop")
        if not intent.get("quantity") or intent.get("quantity") == 0:
            missing_fields.append("quantity")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # Step 6: If fields are missing, generate voice recommendation
        if missing_fields:
            recommendation_text = voice_service.generate_missing_field_prompt(missing_fields, language_code)
            
            return EnhancedVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript=transcription_result['transcript'],
                    confidence=transcription_result['confidence'],
                    alternatives=transcription_result.get('alternatives', []),
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                intent=intent,
                missing_fields=missing_fields,
                recommendation=VoiceRecommendationResponse(
                    missing_fields=missing_fields,
                    recommendation_text=recommendation_text,
                    audio_available=True,
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                available_storages=[],
                booking=None,
                voice_storage=voice_storage_info,
                success=False,
                message=f"Missing required information: {', '.join(missing_fields)}",
                requires_more_info=True
            )
        
        # Step 7: All fields present, proceed with booking
        ai_request = AIQueryRequest(
            farmer_query=farmer_query,
            farmer_lat=farmer_lat,
            farmer_lng=farmer_lng,
            farmer_name=farmer_name,
            farmer_phone=farmer_phone
        )
        
        # Search for available storage
        search_result = ai_query(ai_request, db)
        
        if not search_result.available_storages:
            return EnhancedVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript=transcription_result['transcript'],
                    confidence=transcription_result['confidence'],
                    alternatives=transcription_result.get('alternatives', []),
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                intent=intent,
                missing_fields=[],
                recommendation=None,
                available_storages=[],
                booking=None,
                voice_storage=voice_storage_info,
                success=False,
                message="No available cold storage found matching your requirements",
                requires_more_info=False
            )
        
        # Create booking
        booking_result = ai_book(ai_request, db)
        
        return EnhancedVoiceBookingResponse(
            transcription=VoiceTranscriptionResponse(
                transcript=transcription_result['transcript'],
                confidence=transcription_result['confidence'],
                alternatives=transcription_result.get('alternatives', []),
                language_detected=language_code,
                processing_time_ms=processing_time
            ),
            intent=intent,
            missing_fields=[],
            recommendation=None,
            available_storages=search_result.available_storages,
            booking=booking_result.get('booking'),
            voice_storage=voice_storage_info,
            success=booking_result.get('success', False),
            message=booking_result.get('message', ''),
            requires_more_info=False
        )
        
    except Exception as e:
        processing_time = int((time.time() - start_time) * 1000)
        
        return EnhancedVoiceBookingResponse(
            transcription=VoiceTranscriptionResponse(
                transcript="",
                confidence=0.0,
                alternatives=[],
                language_detected=language_code,
                processing_time_ms=processing_time
            ),
            intent={},
            missing_fields=["system_error"],
            recommendation=None,
            available_storages=[],
            booking=None,
            voice_storage=None,
            success=False,
            message=f"Enhanced voice booking failed: {str(e)}",
            requires_more_info=True
        )

# 18. List Stored Voice Inputs
@app.get("/api/voice/stored-inputs", response_model=VoiceInputListResponse)
def list_voice_inputs(
    farmer_phone: Optional[str] = None,
    limit: int = 10
):
    """
    List stored voice inputs from S3 bucket
    """
    try:
        voice_inputs = voice_service.list_stored_voice_inputs(farmer_phone, limit)
        
        stored_inputs = [StoredVoiceInput(**input_data) for input_data in voice_inputs]
        
        return VoiceInputListResponse(
            voice_inputs=stored_inputs,
            total_count=len(stored_inputs),
            bucket=voice_service.s3_bucket
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list voice inputs: {str(e)}"
        )

# 19. Test S3 Voice Storage
@app.post("/api/voice/test-s3-storage")
async def test_s3_storage(
    audio_file: UploadFile = File(...),
    farmer_name: str = "Test Farmer",
    farmer_phone: str = "+919999999999",
    language_code: str = "hi-IN"
):
    """
    Test S3 storage functionality for voice inputs
    """
    try:
        # Read audio content
        audio_content = await audio_file.read()
        
        # Store in S3
        farmer_info = {
            'name': farmer_name,
            'phone': farmer_phone
        }
        
        storage_result = voice_service.store_voice_input_s3(audio_content, farmer_info, language_code)
        
        return {
            "test_status": "success",
            "storage_info": storage_result,
            "message": "Voice input successfully stored in S3",
            "s3_bucket": voice_service.s3_bucket,
            "aws_configured": voice_service.s3_client is not None
        }
        
    except Exception as e:
        return {
            "test_status": "error",
            "error": str(e),
            "message": "Failed to store voice input in S3",
            "s3_bucket": voice_service.s3_bucket,
            "aws_configured": voice_service.s3_client is not None
        }