from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date

class ColdStorageCreate(BaseModel):
    name: str
    address: str
    location_lat: float
    location_lng: float
    total_capacity_kg: float = 100000.0
    price_per_kg_per_day: float
    storage_type: str = "multi-commodity"
    supported_crops: str = "all"

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

    class Config:
        json_schema_extra = {
            "example": {
                "farmer_name": "Ramesh Kumar",
                "farmer_phone": "+919876543210",
                "cold_storage_id": 1,
                "quantity_kg": 500.0,
                "booking_date": "2024-03-10",
                "duration_days": 7,
                "crop_type": "potato"
            }
        }

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
    farmer_lat: float
    farmer_lng: float
    crop_type: str
    quantity_kg: float
    start_date: date
    duration_days: int = 1
    max_distance_km: float = 100.0

class StorageSearchResult(BaseModel):
    storage_id: int
    storage_name: str
    address: str
    distance_km: float
    price_per_kg_per_day: float
    price_per_ton_per_day: float
    total_cost: float
    available_capacity_kg: float
    supported_crops: str
    
    class Config:
        from_attributes = True

class SearchResponse(BaseModel):
    count: int
    search_params: dict
    storages: List[StorageSearchResult]

class AIQueryRequest(BaseModel):
    farmer_query: str
    farmer_lat: float
    farmer_lng: float
    farmer_name: Optional[str] = None
    farmer_phone: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "farmer_query": "I want to store 500kg potato",
                "farmer_lat": 28.7041,
                "farmer_lng": 77.1025,
                "farmer_name": "Ramesh Kumar",
                "farmer_phone": "+919876543210"
            }
        }

class AIQueryResponse(BaseModel):
    intent: dict
    available_storages: List[StorageSearchResult]
    booking_suggestion: Optional[dict] = None

class VoiceQueryRequest(BaseModel):
    farmer_lat: float
    farmer_lng: float
    farmer_name: Optional[str] = None
    farmer_phone: Optional[str] = None
    language_code: str = "hi-IN"

class VoiceTranscriptionResponse(BaseModel):
    transcript: str
    confidence: float
    alternatives: List[str]
    language_detected: str
    processing_time_ms: int

class VoiceRecommendationResponse(BaseModel):
    missing_fields: List[str]
    recommendation_text: str
    audio_available: bool
    audio_uri: Optional[str] = None
    language_detected: str
    processing_time_ms: int

class VoiceBookingResponse(BaseModel):
    transcription: VoiceTranscriptionResponse
    intent: dict
    available_storages: List[StorageSearchResult]
    booking: Optional[dict] = None
    success: bool
    message: str

class SmartVoiceBookingResponse(BaseModel):
    transcription: VoiceTranscriptionResponse
    intent: dict
    missing_fields: List[str]
    recommendation: Optional[VoiceRecommendationResponse] = None
    available_storages: List[StorageSearchResult]
    booking: Optional[dict] = None
    success: bool
    message: str
    requires_more_info: bool

class VoiceStorageResponse(BaseModel):
    stored: bool
    s3_key: str
    s3_uri: str
    bucket: str
    size_bytes: int
    timestamp: str

class StoredVoiceInput(BaseModel):
    s3_key: str
    s3_uri: str
    size: int
    last_modified: str
    farmer_name: str
    farmer_phone: str
    language_code: str
    upload_timestamp: str

class VoiceInputListResponse(BaseModel):
    voice_inputs: List[StoredVoiceInput]
    total_count: int
    bucket: str

class EnhancedVoiceBookingResponse(BaseModel):
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

class TextQueryRequest(BaseModel):
    query: str
    lat: float
    lng: float

    class Config:
        json_schema_extra = {
            "example": {
                "query": "I want to store 500kg potato",
                "lat": 28.7041,
                "lng": 77.1025
            }
        }

class StorageResult(BaseModel):
    id: str
    name: str
    address: str
    distance_km: float
    price_per_kg: float
    price_per_ton: float
    total_cost: float
    available_capacity_kg: float
    supported_crops: str
    urgency: str
    storage_type: str

class QueryResponse(BaseModel):
    intent: dict
    results: List[StorageResult]
