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
from .ai import ai_query, ai_book

router = APIRouter()

@router.post("/transcribe", response_model=VoiceTranscriptionResponse)
async def transcribe_voice(
    audio_file: UploadFile = File(...),
    language_code: str = "hi-IN"
):
    """Transcribe voice input to text using Amazon Transcribe."""
    start_time = time.time()
    
    if not audio_file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    try:
        audio_content = await audio_file.read()
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
async def voice_query(
    audio_file: UploadFile = File(...),
    farmer_lat: float = Form(...),
    farmer_lng: float = Form(...),
    farmer_name: Optional[str] = Form(None),
    farmer_phone: Optional[str] = Form(None),
    language_code: str = Form("hi-IN"),
    db: Session = Depends(get_db)
):
    """Complete voice-to-storage-search workflow."""
    try:
        audio_content = await audio_file.read()
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            raise HTTPException(status_code=500, detail="Voice transcription failed")
        
        ai_request = AIQueryRequest(
            farmer_query=transcription_result['transcript'],
            farmer_lat=farmer_lat,
            farmer_lng=farmer_lng,
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

@router.post("/book", response_model=VoiceBookingResponse)
async def voice_book(
    audio_file: UploadFile = File(...),
    farmer_lat: float = Form(...),
    farmer_lng: float = Form(...),
    farmer_name: str = Form(...),
    farmer_phone: str = Form(...),
    language_code: str = Form("hi-IN"),
    db: Session = Depends(get_db)
):
    """Complete voice-to-booking workflow."""
    start_time = time.time()
    
    try:
        audio_content = await audio_file.read()
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        
        if transcription_result['status'] != 'completed':
            return VoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript="", confidence=0.0, alternatives=[],
                    language_detected=language_code,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ),
                intent={}, available_storages=[], booking=None,
                success=False, message="Voice transcription failed"
            )
        
        ai_request = AIQueryRequest(
            farmer_query=transcription_result['transcript'],
            farmer_lat=farmer_lat,
            farmer_lng=farmer_lng,
            farmer_name=farmer_name,
            farmer_phone=farmer_phone
        )
        
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
            intent=booking_result.get("intent", {}),
            available_storages=[],
            booking=booking_result.get("booking"),
            success=booking_result.get("success", False),
            message=booking_result.get("message", "")
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Voice booking failed: {str(e)}")

@router.post("/test")
async def test_voice_service():
    """Test endpoint to verify voice service configuration."""
    try:
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

@router.post("/smart-book", response_model=SmartVoiceBookingResponse)
async def smart_voice_book(
    audio_file: UploadFile = File(...),
    farmer_lat: float = Form(...),
    farmer_lng: float = Form(...),
    farmer_name: str = "Unknown Farmer",
    farmer_phone: str = "+919999999999",
    language_code: str = "hi-IN",
    db: Session = Depends(get_db)
):
    """Smart voice booking with missing field detection and voice recommendations."""
    start_time = time.time()
    
    try:
        audio_content = await audio_file.read()
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
        
        missing_fields = []
        if not intent.get("crop") or intent.get("crop") == "unknown":
            missing_fields.append("crop")
        if not intent.get("quantity") or intent.get("quantity") == 0:
            missing_fields.append("quantity")
        
        processing_time = int((time.time() - start_time) * 1000)
        
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
                intent=intent, missing_fields=missing_fields,
                recommendation=VoiceRecommendationResponse(
                    missing_fields=missing_fields,
                    recommendation_text=recommendation_text,
                    audio_available=True,
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                available_storages=[], booking=None,
                success=False, message=f"Missing required information: {', '.join(missing_fields)}",
                requires_more_info=True
            )
        
        ai_request = AIQueryRequest(
            farmer_query=farmer_query, farmer_lat=farmer_lat, farmer_lng=farmer_lng,
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
        
        booking_result = ai_book(ai_request, db)
        
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
async def get_recommendation_audio(
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

@router.post("/enhanced-book", response_model=EnhancedVoiceBookingResponse)
async def enhanced_voice_book(
    audio_file: UploadFile = File(...),
    farmer_lat: float = Form(...),
    farmer_lng: float = Form(...),
    farmer_name: str = Form("Unknown Farmer"),
    farmer_phone: str = Form("+919999999999"),
    language_code: str = Form("hi-IN"),
    store_in_s3: bool = Form(True),
    confirmed: bool = Form(False),
    db: Session = Depends(get_db)
):
    """Enhanced voice booking with S3 storage and confirmation flow."""
    start_time = time.time()
    
    try:
        audio_content = await audio_file.read()
        
        voice_storage_info = None
        if store_in_s3:
            farmer_info = {'name': farmer_name, 'phone': farmer_phone}
            storage_result = voice_service.store_voice_input_s3(audio_content, farmer_info, language_code)
            voice_storage_info = VoiceStorageResponse(**storage_result)
        
        transcription_result = voice_service.transcribe_audio_bytes(audio_content, language_code)
        if transcription_result['status'] != 'completed':
            return EnhancedVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript="", confidence=0.0, alternatives=[],
                    language_detected=language_code,
                    processing_time_ms=int((time.time() - start_time) * 1000)
                ),
                intent={}, missing_fields=["transcription_failed"],
                recommendation=None, available_storages=[], booking=None,
                voice_storage=voice_storage_info, success=False,
                message="Voice transcription failed", requires_more_info=True
            )
        
        farmer_query = transcription_result['transcript']
        intent = extract_farmer_intent(farmer_query)
        
        # Log Interaction
        interaction = InteractionLog(
            interaction_type="voice", query_text=farmer_query,
            extracted_intent=json.dumps(intent),
            s3_voice_uri=voice_storage_info.s3_uri if voice_storage_info else None,
            location_lat=farmer_lat, location_lng=farmer_lng
        )
        db.add(interaction)
        db.commit()
        
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
            audio_uri = None
            try:
                polly_audio = voice_service.generate_voice_recommendation(recommendation_text, language_code)
                audio_uri = voice_service.store_recommendation_audio_s3(polly_audio, language_code)
            except Exception as polly_err:
                print(f"Polly generation failed: {polly_err}")

            return EnhancedVoiceBookingResponse(
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
                    processing_time_ms=0
                ),
                available_storages=[], booking=None,
                voice_storage=voice_storage_info, success=False,
                message=f"Missing required information: {', '.join(missing_fields)}",
                requires_more_info=True
            )
        
        ai_request = AIQueryRequest(
            farmer_query=farmer_query, farmer_lat=farmer_lat, farmer_lng=farmer_lng,
            farmer_name=farmer_name, farmer_phone=farmer_phone
        )
        
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
                intent=intent, missing_fields=[], recommendation=None,
                available_storages=[], booking=None,
                voice_storage=voice_storage_info, success=False,
                message="No available cold storage found matching your requirements",
                requires_more_info=False
            )
        
        if not confirmed:
            suggestion = search_result.booking_suggestion
            truck_msg = f"We found shared truck options for your {intent.get('crop', 'produce')} starting from ₹200. "
            pricing_msg = f"The storage cost will be ₹{suggestion['total_cost']} for {suggestion['duration_days']} days."
            
            return EnhancedVoiceBookingResponse(
                transcription=VoiceTranscriptionResponse(
                    transcript=transcription_result['transcript'],
                    confidence=transcription_result['confidence'],
                    alternatives=transcription_result.get('alternatives', []),
                    language_detected=language_code,
                    processing_time_ms=processing_time
                ),
                intent=intent, missing_fields=[], recommendation=None,
                available_storages=search_result.available_storages,
                booking=suggestion,
                voice_storage=voice_storage_info, success=True,
                message=f"{pricing_msg} {truck_msg} Please confirm if you agree to book.",
                requires_more_info=False
            )

        booking_result = ai_book(ai_request, db)
        
        return EnhancedVoiceBookingResponse(
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
            voice_storage=voice_storage_info,
            success=booking_result.get('success', False),
            message=booking_result.get('message', ''),
            requires_more_info=False
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
