from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List
import time
import json

from ....core.database import get_db
from ....models import InteractionLog
from ....schemas import (
    VoiceTranscriptionResponse, VoiceBookingResponse,
    AIQueryRequest, SmartVoiceBookingResponse,
    VoiceRecommendationResponse, EnhancedVoiceBookingResponse,
    VoiceStorageResponse, VoiceInputListResponse,
    StoredVoiceInput
)
from ....voice_service import voice_service
from ....ai_service import extract_farmer_intent
from .ai import ai_query, ai_book as ai_book_internal

router = APIRouter()

@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
def transcribe_voice(
    audio_file: UploadFile = File(...),
    language_code: str = "hi-IN"
):
    """Transcribe voice input to text using Amazon Transcribe."""
    start_time = time.time()
    
    if not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    try:
        # We need to read the file content synchronously in a regular def function
        audio_content = audio_file.file.read()
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
        raise HTTPException(status_code=500, detail=f"Voice transcription failed: {str(e)}")

@router.post("/query")
@router.post("/voice-query", include_in_schema=False)
def voice_query(
    audio_file: UploadFile = File(...),
    farmer_lat: Optional[float] = Form(None),
    farmer_lng: Optional[float] = Form(None),
    farmer_name: Optional[str] = Form(None),
    farmer_phone: Optional[str] = Form(None),
    language_code: str = Form("hi-IN"),
    db: Session = Depends(get_db)
):
    """Complete voice-to-storage-search workflow."""
    try:
        audio_content = audio_file.file.read()
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            raise HTTPException(status_code=500, detail="Voice transcription failed")
        
        # Default to seeded location if missing
        lat = farmer_lat if farmer_lat is not None else 28.7041
        lng = farmer_lng if farmer_lng is not None else 77.1025
        
        ai_request = AIQueryRequest(
            farmer_query=transcription_result['transcript'],
            farmer_lat=lat,
            farmer_lng=lng,
            farmer_name=farmer_name,
            farmer_phone=farmer_phone
        )
        
        ai_result = ai_query(ai_request, db)
        
        return {
            "transcription": {
                "transcript": transcription_result['transcript'],
                "confidence": transcription_result['confidence'],
                "alternatives": transcription_result.get('alternatives', []),
                "language_detected": language_code,
                "processing_time_ms": 0
            },
            "intent": ai_result.intent,
            "available_storages": ai_result.available_storages,
            "booking_suggestion": ai_result.booking_suggestion
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice query processing failed: {str(e)}")

@router.post("/book", response_model=SmartVoiceBookingResponse)
@router.post("/voice-book", response_model=SmartVoiceBookingResponse, include_in_schema=False)
def voice_book(
    audio_file: UploadFile = File(...),
    farmer_lat: Optional[float] = Form(None),
    farmer_lng: Optional[float] = Form(None),
    farmer_name: str = Form("Unknown Farmer"),
    farmer_phone: str = Form("+919999999999"),
    language_code: str = Form("hi-IN"),
    db: Session = Depends(get_db)
):
    """Smart voice booking with missing field detection and voice recommendations."""
    start_time = time.time()
    
    try:
        audio_content = audio_file.file.read()
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            return SmartVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript="", confidence=0.0, alternatives=[],
                    language_detected=language_code,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ),
                intent={}, missing_fields=["transcription_failed"],
                recommendation=None, available_storages=[], booking=None,
                success=False, message="Voice transcription failed",
                requires_more_info=True
            )
        
        farmer_query = transcription_result['transcript']
        intent = extract_farmer_intent(farmer_query)
        
        # Default to seeded location if missing
        lat = farmer_lat if farmer_lat is not None else 28.7041
        lng = farmer_lng if farmer_lng is not None else 77.1025
        
        missing_fields = []
        if not intent.get("crop") or intent.get("crop") == "unknown":
            missing_fields.append("crop")
        if not intent.get("quantity") or intent.get("quantity") == 0:
            missing_fields.append("quantity")
        if not intent.get("time") or intent.get("time") == "unknown":
            missing_fields.append("time")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if missing_fields:
            recommendation_text = voice_service.generate_missing_field_prompt(missing_fields, language_code)
            
            # Generate Audio for the recommendation (Interactive Voice Response)
            audio_uri = None
            try:
                # Generate MP3 using Polly
                polly_audio = voice_service.generate_voice_recommendation(recommendation_text, language_code)
                # Store in S3 and get URI
                audio_uri = voice_service.store_recommendation_audio_s3(polly_audio, language_code)
            except Exception as e:
                print(f"⚠️ Voice recommendation generation failed: {e}")
            
            return SmartVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript=transcription_result['transcript'],
                    confidence=transcription_result['confidence'],
                    alternatives=transcription_result.get('alternatives', []),
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                intent=intent, missing_fields=missing_fields,
                recommendation=VoiceRecommendationResponse(
                    missing_fields=missing_fields,
                    recommendation_text=recommendation_text,
                    audio_available=audio_uri is not None,
                    audio_uri=audio_uri,
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                available_storages=[], booking=None,
                success=False, message=f"Missing required information: {', '.join(missing_fields)}",
                requires_more_info=True
            )
        
        ai_request = AIQueryRequest(
            farmer_query=farmer_query, farmer_lat=lat, farmer_lng=lng,
            farmer_name=farmer_name, farmer_phone=farmer_phone
        )
        
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
                intent=intent, missing_fields=[], recommendation=None,
                available_storages=[], booking=None,
                success=False, message="No available cold storage found matching your requirements",
                requires_more_info=False
            )
        
        booking_result = ai_book_internal(ai_request, db)
        
        return SmartVoiceBookingResponse(
            transcription=VoiceTranscriptionResponse(
                transcript=transcription_result['transcript'],
                confidence=transcription_result['confidence'],
                alternatives=transcription_result.get('alternatives', []),
                language_detected=language_code,
                processing_time_ms=processing_time
            ),
            intent=intent, missing_fields=[], recommendation=None,
            available_storages=search_result.available_storages,
            booking=booking_result.get('booking'),
            success=booking_result.get('success', False),
            message=booking_result.get('message', ''),
            requires_more_info=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/recommendation-audio")
def get_recommendation_audio(
    missing_fields: List[str],
    language_code: str = "hi-IN"
):
    """Generate voice recommendation audio for missing fields."""
    try:
        recommendation_text = voice_service.generate_missing_field_prompt(missing_fields, language_code)
        audio_bytes = voice_service.generate_voice_recommendation(recommendation_text, language_code)
        
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=recommendation.mp3",
                "X-Recommendation-Text": recommendation_text
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice recommendation generation failed: {str(e)}")



@router.get("/stored-inputs", response_model=VoiceInputListResponse)
def list_voice_inputs(
    farmer_phone: Optional[str] = None,
    limit: int = 10
):
    """List stored voice inputs from S3 bucket."""
    try:
        voice_inputs = voice_service.list_stored_voice_inputs(farmer_phone, limit)
        stored_inputs = [StoredVoiceInput(**input_data) for input_data in voice_inputs]
        
        return VoiceInputListResponse(
            voice_inputs=stored_inputs,
            total_count=len(stored_inputs),
            bucket=voice_service.s3_bucket
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list voice inputs: {str(e)}")

@router.post("/test-s3-storage")
async def test_s3_storage(
    audio_file: UploadFile = File(...),
    farmer_name: str = "Test Farmer",
    farmer_phone: str = "+919999999999",
    language_code: str = "hi-IN"
):
    """Test S3 storage functionality for voice inputs."""
    try:
        audio_content = await audio_file.read()
        farmer_info = {'name': farmer_name, 'phone': farmer_phone}
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
