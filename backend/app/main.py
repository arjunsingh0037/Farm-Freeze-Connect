from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api.v1.router import api_router
from .core.database import engine, Base
from .core.config import settings

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables on startup
    print("🚀 Initializing database tables...")
    Base.metadata.create_all(bind=engine)
    yield
    # Clean up on shutdown if needed
    print("🛑 Shutting down application...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FarmFreeze Connect - Cold Storage Booking System",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")
# Support old paths for backward compatibility if needed, or redirect
app.include_router(api_router, prefix="/api") # For paths like /api/bookings
app.include_router(api_router) # For paths like /text-query

@app.get("/")
def root():
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
