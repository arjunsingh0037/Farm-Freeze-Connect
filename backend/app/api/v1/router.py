from fastapi import APIRouter
from .endpoints import storages, farmers, bookings, ai, voice, analytics

api_router = APIRouter()

api_router.include_router(storages.router, prefix="/cold-storages", tags=["cold-storages"])
api_router.include_router(farmers.router, prefix="/farmers", tags=["farmers"])
api_router.include_router(bookings.router, prefix="/bookings", tags=["bookings"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
