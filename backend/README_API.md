# FarmFreeze Connect - POC API Documentation

This backend service provides AI-powered cold storage booking capabilities for farmers.

## Base URL
`http://localhost:8000`

## Core POC Endpoints

### 1. Smart Voice Booking (Primary Demo Flow)
**Endpoint**: `POST /api/v1/voice/book`
- **Purpose**: Handles the complete voice-to-booking journey.
- **Features**:
  - Transcribes Hindi/English voice input.
  - Extracts intent (Crop, Quantity, Time).
  - Checks if critical info is missing.
  - Returns **Booking Confirmation** OR **Audio Prompt** to ask for missing details.
- **Input**: `audio_file` (wav/mp3), `language_code` (default: "hi-IN").
- **Example Response (Success)**:
  ```json
  {
    "success": true,
    "booking": { "booking_reference": "FF-12345", ... },
    "message": "Booking created successfully"
  }
  ```
- **Example Response (Missing Info)**:
  ```json
  {
    "success": false,
    "requires_more_info": true,
    "recommendation": {
      "audio_available": true,
      "audio_uri": "s3://...", 
      "recommendation_text": "नमस्ते, आप कौन सी फसल स्टोर करना चाहते हैं?"
    }
  }
  ```

### 2. Text Search
**Endpoint**: `POST /api/v1/ai/query-ai`
- **Purpose**: Text-based search for storage availability.
- **Input JSON**:
  ```json
  {
    "farmer_query": "I want to store 500kg potato",
    "farmer_lat": 28.7041,
    "farmer_lng": 77.1025
  }
  ```

### 3. List Cold Storages
**Endpoint**: `GET /api/v1/cold-storages/`
- **Purpose**: Returns list of all available facilities (seeded data).

### 4. Create Booking (Direct)
**Endpoint**: `POST /api/v1/bookings/`
- **Purpose**: Manual booking creation without AI.

## Fallback Mechanisms (Robustness)
- **Database**: Tries AWS RDS → Falls back to **Local SQLite**.
- **Voice**: Tries AWS Transcribe → Returns **Error** (No mock data).
- **AI**: Tries AWS Bedrock → Tries Claude API → Returns **Error** (No mock data).
- **Location**: Tries User Location → Falls back to **Delhi (Seeded Region)**.

## Setup
1. Ensure `.env` has valid AWS credentials.
2. Run server: `uvicorn app.main:app --reload`
