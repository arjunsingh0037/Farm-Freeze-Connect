# Design Document
## Project: Farm-Freeze Connect
## Team: EigenMinds

---

# 1. System Architecture Overview

Farm-Freeze Connect follows a cloud-native, AI-driven microservices architecture deployed on AWS.

Users:
- Farmers (Voice/SMS/USSD)
- Cold Storage Operators
- Admin Dashboard

Core Components:
- Voice Gateway Layer
- Backend API
- AI/ML Services
- Database Layer
- Payment Layer
- Notification Engine

---

# 2. High-Level Architecture

Farmer (USSD/IVR/SMS/WhatsApp)
        |
Voice/SMS Gateway (Twilio / Exotel)
        |
API Layer (Node.js)
        |
-------------------------------------
| Storage Service
| Booking Service
| AI Grouping Engine
| Harvest Prediction Engine
| Pricing Engine
| Quality Grading Service
-------------------------------------
        |
PostgreSQL + Redis
        |
AWS Infrastructure (EC2, S3, Lambda)

---

# 3. Technology Stack

Voice/SMS:
- Twilio (USSD)
- Exotel (IVR)
- WhatsApp Business API

AI/ML:
- TensorFlow (Quality grading)
- Google Earth Engine (Harvest prediction)

Backend:
- Node.js (Express)
- PostgreSQL
- Redis

Maps & Location:
- Google Maps API
- PostGIS (50km radius search)

Payments:
- Razorpay UPI
- PM-KISAN integration

Cloud:
- AWS EC2
- AWS S3
- AWS Lambda
- AWS RDS

---

# 4. Database Design (Simplified)

Farmers
- id
- name
- phone
- language
- location

ColdStorageUnits
- id
- name
- location
- capacity
- available_slots
- pricing

Bookings
- id
- farmer_id
- storage_id
- quantity
- booking_date
- status

FarmerGroups
- id
- route
- farmers_list
- transport_cost

QualityReports
- id
- farmer_id
- grade
- recommendation

---

# 5. AI Design

## 5.1 Harvest Prediction Model
Input:
- Satellite imagery
- Crop type
- Historical yield

Model:
- Time-series + vegetation index analysis

Output:
- Harvest readiness score
- Auto-book trigger 72 hours before maturity

---

## 5.2 Farmer Grouping Engine

Input:
- Farmer geolocation
- Storage destination
- Harvest date

Algorithm:
- Route clustering (K-Means / DBSCAN)
- Distance optimization
- Cost minimization

Output:
- Shared transport grouping
- Cost per farmer

---

## 5.3 Dynamic Pricing Engine

Inputs:
- Demand levels
- Storage occupancy
- Seasonal data

Model:
- Demand forecasting
- Elastic pricing model

Output:
- Per kg pricing recommendation

---

## 5.4 Quality Grading Model

Input:
- Camera image of produce

Model:
- CNN classification (A/B/C grade)

Output:
- Storage duration recommendation
- Expected price uplift

---

# 6. Security Design

- JWT authentication
- Role-based access
- HTTPS enforced
- Encrypted payment processing
- Rate limiting for API abuse

---

# 7. Deployment Architecture

- Dockerized services
- CI/CD via GitHub Actions
- Deployed on AWS EC2
- Auto-scaling enabled
- Redis caching for high-load

---

# 8. Scalability Strategy

- Microservices architecture
- Separate AI service scaling
- Read replicas for database
- CDN for static resources

---

# 9. Cost Optimization

- Serverless Lambda for event triggers
- On-demand compute scaling
- Use of existing 8,698 cold storage facilities (no capex)
