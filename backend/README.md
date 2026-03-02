# 🌾 FarmFreeze Connect Backend

AI-Powered Cold Storage Marketplace for Smallholder Farmers

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [AI Components](#ai-components)
- [Deployment](#deployment)
- [Project Structure](#project-structure)

## Overview

FarmFreeze Connect is an AI-powered platform that helps smallholder farmers in India access nearby cold storage facilities in real-time. The platform addresses the critical gap between existing cold storage infrastructure (8,698 units) and farmer accessibility.

### Problem Statement

- **₹92,651 crore** lost annually in post-harvest losses
- **40 million tons** of fruits/vegetables wasted due to cold chain gaps
- **86%** of small farmers (<2 hectares) cannot access cold storage effectively

### Our Solution

An AI-powered multilingual marketplace that:
- Provides real-time cold storage availability
- Uses voice-based AI assistant for non-English speakers
- Recommends optimal storage based on distance, price, and availability
- Enables instant booking and capacity management

## Features

### Core Features
- 🧊 **Real-time Availability** - Live capacity tracking across cold storage facilities
- 📦 **Booking Management** - Complete booking lifecycle with capacity auto-update
- 📍 **Location-based Search** - Find nearby cold storage within specified radius
- 💰 **Transparent Pricing** - Clear pricing per kg/day

### AI-Powered Features
- 🎙️ **Voice Assistant** - Understands natural language in Tamil, Hindi, Telugu, and more
- 🤖 **Smart Recommendations** - Multi-factor scoring for optimal storage matching
- 🌐 **Multilingual Support** - 22+ Indian languages support
- 📊 **Demand Prediction** - Basic trend analysis for capacity planning

### Admin Features
- 📈 **Dashboard** - Real-time analytics and utilization metrics
- 📋 **Capacity Management** - Update and track storage capacity
- 📊 **Booking Analytics** - Historical trends and reporting

## Tech Stack

### Backend
- **Language:** Python 3.9+
- **Framework:** FastAPI
- **Database:** PostgreSQL (AWS RDS)
- **ORM:** SQLAlchemy

### AI Services (AWS)
- **Amazon Transcribe** - Speech to text
- **Amazon Translate** - Language translation
- **Amazon Bedrock** - LLM for entity extraction and reasoning

### Infrastructure
- **Deployment:** AWS Lambda + API Gateway
- **SMS:** AWS SNS
- **Authentication:** AWS Cognito

### Additional
- **Testing:** Pytest
- **Container:** Docker
- **Documentation:** Swagger/OpenAPI

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (PWA)                           │
│         React/Next.js with Voice Interface                  │
└─────────────────────────┬───────────────────────────────────┘
                          │ REST API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   API Gateway                                │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Cold Storage│  │  Booking    │  │  AI Recommendation  │  │
│  │   Service   │  │  Service    │  │      Engine         │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐  ┌─────────────┐                           │
│  │   Farmer    │  │  Capacity   │                           │
│  │   Service   │  │  Manager    │                           │
│  └─────────────┘  └─────────────┘                           │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                   PostgreSQL Database                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │Cold Storages│  │  Farmers    │  │     Bookings        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                    AWS AI Services                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Transcribe│  │  Translate  │  │      Bedrock        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL 13+
- AWS Account (for AI services)
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Set up database**
```bash
# Create PostgreSQL database
createdb farmfreeze

# Run migrations (auto-creates tables)
python -m app.main
```

6. **Start the server**
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://postgres:password@localhost:5432/farmfreeze

# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# AI Services
BEDROCK_MODEL_ID=anthropic.claude-v2

# Application
DEBUG=true
SECRET_KEY=your-secret-key
```

## API Documentation

### Base URL
- **Development:** `http://localhost:8000/api/v1`
- **Swagger Docs:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Endpoints

#### Cold Storage
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/cold-storages` | List nearby storages |
| GET | `/api/v1/cold-storages/{id}` | Get storage details |
| POST | `/api/v1/cold-storages` | Create storage (admin) |
| PUT | `/api/v1/cold-storages/{id}` | Update storage (admin) |
| PUT | `/api/v1/cold-storages/{id}/capacity` | Update capacity |
| GET | `/api/v1/cold-storages/{id}/utilization` | Get utilization |

#### Farmers
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/farmers` | Register farmer |
| POST | `/api/v1/farmers/login` | Login by phone |
| GET | `/api/v1/farmers/{id}` | Get farmer details |
| PUT | `/api/v1/farmers/{id}` | Update farmer |
| GET | `/api/v1/farmers/{id}/bookings` | Get farmer bookings |

#### Bookings
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/bookings` | Create booking |
| GET | `/api/v1/bookings/{id}` | Get booking details |
| GET | `/api/v1/bookings/reference/{ref}` | Get by reference |
| PUT | `/api/v1/bookings/{id}/cancel` | Cancel booking |
| GET | `/api/v1/bookings/farmer/{id}` | Get farmer bookings |

#### AI Recommendations
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/ai/voice-query` | Process voice query |
| POST | `/api/v1/ai/recommend` | Get recommendations |
| GET | `/api/v1/ai/explain-recommendation/{id}` | Explain recommendation |

#### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/dashboard` | Dashboard stats |
| GET | `/api/v1/admin/storages` | All storages |
| GET | `/api/v1/admin/bookings` | All bookings |
| GET | `/api/v1/admin/utilization` | Overall utilization |
| GET | `/api/v1/admin/booking-trends` | Booking trends |

### Example API Calls

#### Search Nearby Cold Storages
```bash
curl -X GET "http://localhost:8000/api/v1/cold-storages?lat=12.92&lng=79.13&radius_km=50"
```

#### Create Booking
```bash
curl -X POST "http://localhost:8000/api/v1/bookings" \
  -H "Content-Type: application/json" \
  -d '{
    "farmer_id": 1,
    "cold_storage_id": 1,
    "quantity_kg": 500,
    "booking_date": "2024-02-15",
    "duration_days": 3
  }'
```

#### Get AI Recommendations
```bash
curl -X POST "http://localhost:8000/api/v1/ai/recommend" \
  -H "Content-Type: application/json" \
  -d '{
    "location_lat": 12.92,
    "location_lng": 79.13,
    "quantity_kg": 500,
    "crop": "tomato"
  }'
```

## AI Components

### 1. Voice Query Processing
```python
# Uses Amazon Transcribe for speech-to-text
# Uses Amazon Translate for language normalization
# Uses Amazon Bedrock for entity extraction
```

### 2. Recommendation Engine
```python
# Multi-factor scoring algorithm
score = (
    0.35 * normalize(distance) +
    0.30 * normalize(price) +
    0.35 * (1 - normalize(availability))
)
```

### 3. Entity Extraction
```python
# LLM extracts: crop, quantity, date, location intent
# Example: "Kal 2 ton tamatar rakhna hai" → 
# {crop: "tomato", quantity_kg: 2000, required_date: "tomorrow"}
```

### 4. Multilingual Support
- **Tamil (ta-IN):** "Enaku 2 ton thakkali iruku"
- **Hindi (hi-IN):** "Kal 2 ton tamatar rakhna hai"
- **Telugu (te-IN):** "Nenu 2 ton tomato istunnanu"

## Deployment

### AWS Deployment

1. **Create RDS PostgreSQL instance**
2. **Set up AWS Lambda with API Gateway**
3. **Configure AWS AI services (Transcribe, Translate, Bedrock)**
4. **Set up SNS for SMS notifications**
5. **Deploy using AWS SAM or Serverless Framework**

### Docker Deployment

```bash
# Build image
docker build -t farmfreeze-backend .

# Run container
docker run -p 8000:8000 --env-file .env farmfreeze-backend
```

### Environment-Specific Configurations

#### Development
```env
DEBUG=true
DATABASE_URL=postgresql://localhost:5432/farmfreeze
```

#### Production
```env
DEBUG=false
DATABASE_URL=postgresql://prod-host:5432/farmfreeze
AWS_ACCESS_KEY_ID=prod-key
```

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── config.py                  # Configuration settings
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py          # Database connection
│   │   └── models.py              # SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── cold_storage.py        # Cold storage schemas
│   │   ├── farmer.py              # Farmer schemas
│   │   ├── booking.py             # Booking schemas
│   │   └── ai.py                  # AI-related schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── cold_storages.py       # Cold storage endpoints
│   │   ├── farmers.py             # Farmer endpoints
│   │   ├── bookings.py            # Booking endpoints
│   │   ├── ai.py                  # AI recommendation endpoints
│   │   └── admin.py               # Admin dashboard endpoints
│   └── services/
│       ├── __init__.py
│       ├── recommendation.py      # AI recommendation engine
│       ├── capacity_manager.py    # Capacity management
│       └── notification.py        # SMS notifications
├── requirements.txt
├── .env.example
├── Dockerfile
└── README.md
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_bookings.py -v
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For questions or support, please open an issue on GitHub.

---

Built with ❤️ for Indian Farmers