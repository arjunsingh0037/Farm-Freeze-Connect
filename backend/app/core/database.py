from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from .config import settings

# SQLite Fallback Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "farmfreeze.db")
SQLITE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# Function to test database connection
def test_connection(url, timeout=5):
    """Test database connection with timeout"""
    try:
        connect_args = {}
        if url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        else:
            connect_args = {"connect_timeout": timeout}
        
        temp_engine = create_engine(url, connect_args=connect_args)
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"⚠️  Connection failed: {str(e)[:100]}")
        return False

# Determine DATABASE_URL with RDS primary and SQLite fallback
DATABASE_URL = None
DB_TYPE = "unknown"

# Check if RDS credentials are configured
rds_configured = (
    settings.RDS_HOST and 
    settings.RDS_HOST != "localhost" and 
    settings.RDS_PASSWORD
)

if rds_configured:
    # Try RDS first
    RDS_URL = f"postgresql://{settings.RDS_USER}:{settings.RDS_PASSWORD}@{settings.RDS_HOST}:{settings.RDS_PORT}/{settings.RDS_DB}"
    print(f"🔄 Attempting to connect to RDS PostgreSQL at {settings.RDS_HOST}...")
    
    if test_connection(RDS_URL, timeout=5):
        DATABASE_URL = RDS_URL
        DB_TYPE = "RDS PostgreSQL"
        print(f"✅ Successfully connected to RDS PostgreSQL")
        print(f"   Host: {settings.RDS_HOST}")
        print(f"   Database: {settings.RDS_DB}")
    else:
        print(f"❌ RDS connection failed. Falling back to SQLite...")
        DATABASE_URL = SQLITE_URL
        DB_TYPE = "SQLite (Fallback)"
else:
    # Use SQLite if RDS not configured
    DATABASE_URL = SQLITE_URL
    DB_TYPE = "SQLite (Default)"
    print(f"📦 RDS not configured. Using SQLite database.")

print(f"🗄️  Active Database: {DB_TYPE}")
if DATABASE_URL.startswith("sqlite"):
    print(f"   Path: {SQLITE_DB_PATH}")

# SQLAlchemy Engine Configuration
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # PostgreSQL connection settings
    connect_args = {
        "connect_timeout": 10,
        "options": "-c timezone=utc"
    }

# Create engine with appropriate settings
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False           # Set to True for SQL query logging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

