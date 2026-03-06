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

# Include API routers
app.include_router(api_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api")

# Explicit root-level routes for the exact prompt requirements (POST /query and POST /book)
from .api.v1.endpoints.ai import router as ai_router
from .api.v1.endpoints.bookings import router as booking_router

# These allow for POST /query and POST /book directly as requested
app.include_router(ai_router, tags=["root-ai"])
app.include_router(booking_router, tags=["root-bookings"])

@app.get("/")
def root():
    return {
        "message": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "active"
    }

if __name__ == "__main__":
    import uvicorn
    # Use "app.main:app" if running from the "backend" directory
    # Use "backend.app.main:app" if running from the root directory
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
