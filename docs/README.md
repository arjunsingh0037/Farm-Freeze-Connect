# 🌾 FarmFreeze Connect

Smart Cold Storage Booking System for Indian Farmers with AI-powered voice and text interfaces.

## 🎯 Features

### Voice Interface
- 🎤 Record voice in Hindi or English
- 🗣️ Natural language understanding
- 📁 Audio file upload support
- 🤖 AI-powered intent extraction

### Text Interface
- 💬 Natural language text queries
- 🔍 Intelligent storage matching
- 📊 Real-time availability checking

### Smart Booking
- 📍 Location-based storage search
- 💰 Automatic cost calculation
- ⏱️ Duration-based pricing
- ✅ One-click booking confirmation

### AI Services
- 🧠 AWS Bedrock (Primary)
- 🔄 Claude API (Fallback)
- 📝 Mock data (Development)

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd FarmfreezeConnect
```

2. **Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

3. **Configure environment**
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API keys
# AWS_ACCESS_KEY_ID=your_aws_key
# AWS_SECRET_ACCESS_KEY=your_aws_secret
# CLAUDE_API_KEY=your_claude_key
```

4. **Initialize database**
```bash
# Add cold storage data
python populate_cold_storages.py
```

### Running the Application

**Option 1: Run Everything (Recommended)**
```bash
.\start_all.bat
```
This will:
- Start backend on http://localhost:8001
- Start frontend on http://localhost:3000
- Open browser automatically

**Option 2: Run Separately**

Backend:
```bash
.\start.bat
# or
cd backend
python -m uvicorn app.main:app --reload --port 8001
```

Frontend:
```bash
.\start_frontend.bat
# or
cd frontend
python -m http.server 3000
```

## 📁 Project Structure

```
FarmfreezeConnect/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/v1/endpoints/  # API routes
│   │   ├── core/              # Database & config
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── ai_service.py      # AI processing
│   │   ├── voice_service.py   # Voice processing
│   │   └── main.py            # FastAPI app
│   ├── .env                   # Configuration
│   └── requirements.txt       # Dependencies
│
├── frontend/                   # Web interface
│   ├── index.html             # Main page
│   ├── styles.css             # Styling
│   ├── app.js                 # Application logic
│   └── README.md              # Frontend docs
│
├── voice.py                   # CLI voice interface
├── populate_cold_storages.py  # Database seeding
├── view_database.py           # Database viewer
├── view_bookings.py           # Bookings viewer
├── start.bat                  # Backend starter
├── start_frontend.bat         # Frontend starter
├── start_all.bat              # Full stack starter
└── README.md                  # This file
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret

# Claude API (Fallback)
CLAUDE_API_KEY=your_claude_key

# S3 Storage
S3_BUCKET_NAME=farmfreeze-voice-uploads

# Database
DATABASE_URL=sqlite:///./farmfreeze.db

# Application
DEBUG=true
APP_NAME=FarmFreeze Connect
APP_VERSION=1.0.0
```

## 📡 API Endpoints

### Voice Endpoints
- `POST /api/v1/voice/enhanced-book` - Complete voice booking
- `POST /api/v1/voice/transcribe` - Transcribe audio only
- `POST /api/v1/voice/query` - Voice query without booking

### AI Endpoints
- `POST /api/v1/ai/query` - Text query processing
- `POST /api/v1/ai/book` - AI-powered booking

### Storage Endpoints
- `GET /api/v1/cold-storages` - List all storages
- `POST /api/v1/cold-storages` - Create storage
- `GET /api/v1/cold-storages/{id}` - Get storage details

### Booking Endpoints
- `POST /api/v1/bookings` - Create booking
- `GET /api/v1/bookings` - List all bookings

### Documentation
- `GET /docs` - Interactive API documentation (Swagger)
- `GET /redoc` - Alternative API documentation

## 🎤 Usage Examples

### Voice Booking (CLI)
```bash
python voice.py
# Select option 1 or 2 to record
# Speak: "I need to store 100 kg tomatoes from tomorrow"
```

### Voice Booking (Web)
1. Open http://localhost:3000
2. Click "Start Recording"
3. Speak your requirements
4. Click "Stop Recording"
5. Review results and book

### Text Query (Web)
1. Open http://localhost:3000
2. Type: "I need to store 50 kg potatoes for 5 days"
3. Click "Find Storage"
4. Review results and book

### Text Query (API)
```bash
curl -X POST http://localhost:8001/api/v1/ai/query \
  -H "Content-Type: application/json" \
  -d '{
    "farmer_query": "I need to store 100 kg tomatoes",
    "farmer_lat": 28.6139,
    "farmer_lng": 77.2090
  }'
```

## 🗄️ Database Management

### View Cold Storages
```bash
python view_database.py
```

### View Bookings
```bash
python view_bookings.py
```

### Add More Storages
```bash
python add_more_storages.py
```

## 🤖 AI Service Fallback Chain

1. **Primary**: AWS Bedrock (Claude 3 Haiku)
   - Best performance
   - Requires AWS credentials

2. **Fallback**: Direct Claude API
   - Activated when Bedrock fails
   - Requires Claude API key

3. **Last Resort**: Mock Data
   - For development/testing
   - No credentials needed

## 🌍 Supported Languages

- Hindi (hi-IN)
- English (en-IN)

## 📊 Database Schema

### ColdStorage
- Location, capacity, pricing
- Supported crops
- Storage type

### Farmer
- Name, phone, location
- Preferences

### Booking
- Farmer + Storage link
- Dates, quantity, cost
- Status tracking

### DailyCapacity
- Real-time availability
- Capacity tracking

## 🔒 Security Notes

- Never commit `.env` file
- Use environment variables for secrets
- Enable CORS only for trusted origins in production
- Validate all user inputs
- Use HTTPS in production

## 🐛 Troubleshooting

### Backend won't start
- Check if port 8001 is available
- Verify Python dependencies installed
- Check `.env` file exists

### Voice recording not working
- Grant microphone permissions
- Use HTTPS or localhost
- Check browser compatibility

### AI service errors
- Verify API keys in `.env`
- Check AWS credentials
- Review fallback chain logs

### Database errors
- Delete `farmfreeze.db` and reinitialize
- Run `populate_cold_storages.py`

## 📝 Development

### Adding New Endpoints
1. Create route in `backend/app/api/v1/endpoints/`
2. Add schema in `backend/app/schemas/schemas.py`
3. Update router in `backend/app/api/v1/router.py`

### Adding New Storage Locations
1. Edit `populate_cold_storages.py`
2. Add storage data
3. Run script to update database

### Modifying Frontend
1. Edit `frontend/index.html` for structure
2. Edit `frontend/styles.css` for styling
3. Edit `frontend/app.js` for functionality

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Test thoroughly
5. Submit pull request

## 📄 License

This project is for educational and demonstration purposes.

## 🙏 Acknowledgments

- AWS Bedrock for AI services
- Anthropic Claude for fallback AI
- FastAPI for backend framework
- SQLAlchemy for database ORM

## 📞 Support

For issues and questions:
- Check troubleshooting section
- Review API documentation at `/docs`
- Check console logs for errors

---

**Built with ❤️ for Indian Farmers**
