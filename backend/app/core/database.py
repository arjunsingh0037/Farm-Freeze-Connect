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
        # Create a throwaway engine with a very short timeout for testing
        temp_engine = create_engine(url, connect_args={"connect_timeout": 3})
        # Try to connect
        with temp_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"⚠️  Connection failed: {str(e)[:100]}")
        return False

# Logic to choose database with fallback
DATABASE_URL = settings.DATABASE_URL or ""

# If we have RDS credentials and DATABASE_URL isn't explicitly local, try to use them first
if settings.RDS_HOST and settings.RDS_HOST != "localhost" and "sqlite" not in str(DATABASE_URL):
    print(f"🔄 Attempting to connect to RDS at {settings.RDS_HOST}...")
    if test_connection(RDS_URL):
        DATABASE_URL = RDS_URL
        print(f"✅ Successfully connected to RDS Database at {settings.RDS_HOST}")
    else:
        # Fallback to local SQLite
        DATABASE_URL = SQLITE_URL
        print(f"❌ RDS Unreachable. Falling back to local SQLite: {SQLITE_DB_PATH}")
elif "sqlite" in str(DATABASE_URL):
    # Explicitly requested SQLite
    DATABASE_URL = SQLITE_URL
    print(f"📦 Explicit SQLite requested: {SQLITE_DB_PATH}")
else:
    # No RDS configured, default to SQLite
    DATABASE_URL = SQLITE_URL
    print(f"📦 No RDS configured. Using local SQLite: {SQLITE_DB_PATH}")

# SQLAlchemy Engine Configuration
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    # SQLite doesn't need pool configuration as much, but can benefit from static pool for in-memory
    engine = create_engine(
        DATABASE_URL, 
        connect_args=connect_args,
        pool_pre_ping=True
    )
else:
    # PostgreSQL / RDS Configuration
    connect_args = {"connect_timeout": 5} # Fail fast on connection
    engine = create_engine(
        DATABASE_URL, 
        connect_args=connect_args,
        pool_size=5,             # Limit pool size to avoid exhaustion
        max_overflow=10,         # Allow some overflow
        pool_timeout=10,         # Wait max 10s for a connection
        pool_recycle=1800,       # Recycle connections every 30 mins
        pool_pre_ping=True       # Check connection health before using
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

