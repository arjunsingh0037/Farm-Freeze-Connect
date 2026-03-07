# 🏗️ FarmFreeze Connect - File-wise Architecture Flow

## 📁 Project Structure & Data Flow

```
farmfreeze-project/
├── 🎤 voice.py                    # Entry Point - Voice Recording
├── 🚀 run_local.py               # Server Launcher
├── ⚙️ local_setup.py             # Development Setup
├── 📊 farmfreeze.db              # SQLite Database
├── 🌐 coming-soon/index.html     # Frontend Placeholder
└── 📦 backend/
    ├── 🔧 .env                   # Configuration
    ├── 📋 requirements.txt       # Dependencies
    └── 🏢 app/
        ├── 🚪 main.py            # FastAPI Application Hub
        ├── ⚙️ config.py          # Settings Manager
        ├── 🤖 ai_service.py      # AI Processing Engine
        └── 🎙️ voice_service.py   # Voice Processing Engine
```

---

## 🔄 Complete Data Flow Architecture

### 1️⃣ **User Interaction Layer**

```
👨‍🌾 Farmer
    ↓ (speaks in Hindi/English)
📱 voice.py
    ├── 🎤 record_voice_live()     # Captures audio using sounddevice
    ├── 📁 tempfile.NamedTemporaryFile()  # Saves to temp .wav file
    └── 🌐 requests.post() → /api/voice/enhanced-book
```

**File: `voice.py`**
- **Input**: Farmer's voice (10 seconds)
- **Processing**: Records audio using `sounddevice` library
- **Output**: Temporary .wav file → API call
- **Example**: "मुझे 100 किलो टमाटर स्टोर करना है कल से"

---

### 2️⃣ **API Gateway Layer**

```
🌐 HTTP Request
    ↓
📦 backend/app/main.py
    ├── 🚪 FastAPI() app instance
    ├── 📊 SQLAlchemy database models
    ├── 🔗 API route handlers
    └── 📤 Response formatting
```

**File: `backend/app/main.py`**
- **Input**: HTTP requests with audio files
- **Processing**: Route handling, request validation
- **Key Endpoints**:
  - `POST /api/voice/enhanced-book` → Complete voice booking
  - `GET /api/v1/cold-storages` → Storage search
  - `POST /api/v1/bookings` → Create booking
- **Output**: JSON responses

---

### 3️⃣ **Voice Processing Pipeline**

```
🎵 Audio File (.wav)
    ↓
🎙️ backend/app/voice_service.py
    ├── 📤 upload_audio_to_s3()           # S3 storage
    ├── 🔄 start_transcription_job()      # Amazon Transcribe
    ├── ⏳ get_transcription_result()     # Polling for results
    ├── 🔊 generate_voice_recommendation() # Amazon Polly
    └── 📝 transcribe_audio_bytes()       # Main workflow
```

**File: `backend/app/voice_service.py`**
- **Input**: Audio bytes from uploaded file
- **AWS Services Used**:
  - **S3**: Store audio files (`s3://farmfreeze-voice-uploads/`)
  - **Transcribe**: Convert speech to text (Hindi/English)
  - **Polly**: Generate voice responses
- **Output**: Transcribed text + confidence score
- **Fallback**: Mock responses when AWS unavailable

---

### 4️⃣ **AI Intelligence Layer (with Fallback)**

```
📝 Transcribed Text
    ↓
🤖 backend/app/ai_service.py
    ├── 🧠 extract_farmer_intent()           # Main AI function
    ├── 🔗 boto3.client('bedrock-runtime')   # AWS Bedrock (Primary)
    ├── 📋 Claude 3 Haiku via Bedrock        # Primary LLM
    ├── ⚠️  Bedrock fails? → Fallback        # Error handling
    ├── 🌐 extract_farmer_intent_claude_api() # Fallback function
    ├── 🔑 requests.post() → Claude API      # Direct Claude API
    └── 🎯 JSON intent extraction            # Structured output
```

**File: `backend/app/ai_service.py`**
- **Input**: Raw transcribed text
- **Primary AI**: Amazon Bedrock - Claude 3 Haiku
- **Fallback AI**: Direct Claude API (claude-3-haiku-20240307)
- **Processing**: Natural language → structured intent
- **Fallback Triggers**:
  - AWS credentials missing
  - Bedrock payment issues
  - Use case details not submitted
  - Network/service errors
- **Output Example**:
```json
{
  "crop": "tomato",
  "quantity": 100,
  "unit": "kg",
  "time": "tomorrow", 
  "urgency": "high",
  "storage_type": "short-term",
  "confidence": 0.85,
  "fallback_used": "bedrock"  // or "claude_api" or "mock"
}
```

---

### 5️⃣ **Configuration & Settings**

```
🔧 Environment Variables
    ↓
⚙️ backend/app/config.py
    ├── 🔑 AWS credentials loading
    ├── 🗄️ Database URL configuration  
    ├── 🤖 AI model settings
    └── 🔒 Security settings
```

**File: `backend/app/config.py`**
- **Input**: Environment variables from `.env`
- **Processing**: Settings validation and defaults
- **Key Configurations**:
  - AWS credentials and regions
  - Database connection strings
  - AI model IDs and parameters
- **Output**: Application-wide settings object

---

### 6️⃣ **Database Layer**

```
📊 SQLAlchemy Models (in main.py)
    ├── 🏪 ColdStorage          # Storage facilities
    ├── 👨‍🌾 Farmer              # User profiles  
    ├── 📋 Booking              # Reservations
    └── 📈 DailyCapacity        # Capacity tracking
        ↓
💾 farmfreeze.db (SQLite)
```

**Database Models in `main.py`:**
- **ColdStorage**: Location, capacity, pricing, supported crops
- **Farmer**: Name, phone, location, preferences
- **Booking**: Links farmers to storage with dates/quantities
- **DailyCapacity**: Real-time availability tracking

---

## 🔄 Complete Request Flow Example

### **Scenario**: Farmer says "मुझे 100 किलो टमाटर स्टोर करना है कल से"

```
1️⃣ voice.py
   📱 Records 10-second audio
   💾 Saves to temp file: /tmp/audio_xyz.wav
   🌐 POST /api/voice/enhanced-book

2️⃣ main.py → enhanced_voice_book()
   📥 Receives multipart form data
   👤 Farmer info: name="Voice User", phone="+919999999999"
   🎵 Audio file: audio_xyz.wav

3️⃣ voice_service.py → transcribe_audio_bytes()
   ☁️ Uploads to S3: s3://farmfreeze-voice-uploads/audio/xyz.wav
   🎙️ Amazon Transcribe: Hindi → "मुझे 100 किलो टमाटर स्टोर करना है कल से"
   📊 Confidence: 0.85

4️⃣ ai_service.py → extract_farmer_intent()
   🤖 First tries Bedrock Claude 3 Haiku
   ⚠️  Bedrock fails → Fallback to Claude API
   🎯 Extracts: {crop: "tomato", quantity: 100, unit: "kg", time: "tomorrow"}
   📊 Adds fallback_used: "claude_api" indicator

5️⃣ main.py → Storage Matching Logic
   📍 Searches cold storages near farmer location
   🏪 Finds: Delhi Cold Storage (5km, ₹0.75/kg/day, 45000kg available)
   📊 Calculates score: distance(35%) + price(30%) + availability(35%)

6️⃣ main.py → Booking Creation
   📋 Creates booking record in database
   📈 Updates DailyCapacity table
   🎫 Generates reference: FF-20260305-001

7️⃣ Response Assembly
   ✅ Success response with booking details
   🔊 Optional: Polly generates voice confirmation
   📤 Returns JSON to voice.py

8️⃣ voice.py → show_result()
   📺 Displays formatted result to farmer
   🎉 Shows booking reference and storage details
```

---

## 🔧 Development & Setup Files

### **Setup Flow**
```
🚀 run_local.py
   ├── 🔍 Checks for backend/.env
   ├── 🌐 Starts uvicorn server on localhost:8000
   └── 🔄 Enables auto-reload for development

⚙️ local_setup.py  
   ├── 📦 Installs: sounddevice, soundfile, numpy
   ├── 📊 Adds sample cold storage data
   └── ✅ Prepares development environment

📋 requirements.txt
   ├── 🚀 FastAPI + uvicorn (web framework)
   ├── 🗄️ SQLAlchemy (database ORM)
   ├── ☁️ boto3 (AWS services)
   └── ⚙️ pydantic + python-dotenv (config)
```

---

## 🌐 API Endpoint Mapping

### **File: `main.py` - Route Handlers**

```python
# Voice Processing Routes
POST /api/voice/enhanced-book        → enhanced_voice_book()
POST /api/voice/transcribe          → transcribe_voice()  
POST /api/voice/query               → voice_query()
GET  /api/voice/recommendation-audio → get_recommendation_audio()

# Core Business Routes  
GET  /api/v1/cold-storages          → get_cold_storages()
POST /api/v1/cold-storages          → create_cold_storage()
POST /api/v1/bookings               → create_booking()
GET  /api/v1/bookings               → get_bookings()

# AI Routes
POST /api/v1/ai/query               → ai_query()
POST /api/v1/ai/book                → ai_book()
```

---

## 🔄 Error Handling & Fallbacks

### **Graceful Degradation with AI Fallback**
```
❌ AWS Bedrock Issues
   ├── � Payment method missing → Claude API fallback
   ├── � Use case details not submitted → Claude API fallback  
   ├── � AWS credentials missing → Claude API fallback
   └── 🌐 Network/service errors → Claude API fallback

❌ Claude API Issues  
   ├── � API key missing → Mock data fallback
   ├── 🌐 Network errors → Mock data fallback
   └── � JSON parsing errors → Mock data fallback

❌ Other Service Issues
   └── 🔄 voice_service.py returns mock transcription
   └── 🔄 Local SQLite database continues working

❌ Audio Recording Issues
   └── 🔄 voice.py accepts file input instead
   └── 🔄 Supports drag-and-drop audio files
```

### **Fallback Priority Order**
1. **Primary**: AWS Bedrock (Claude 3 Haiku)
2. **Fallback**: Direct Claude API (claude-3-haiku-20240307)  
3. **Last Resort**: Mock data for development

### **Configuration Required**
```env
# Primary AI (AWS Bedrock)
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret

# Fallback AI (Direct Claude API)
CLAUDE_API_KEY=your_claude_api_key
```

This architecture ensures the system works even when external services are unavailable, making it robust for development and testing.