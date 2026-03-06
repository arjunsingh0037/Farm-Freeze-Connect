from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from .config import settings

# SQLite Fallback Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "farmfreeze.db")
SQLITE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# RDS URL construction from settings
RDS_URL = f"postgresql://{settings.RDS_USER}:{settings.RDS_PASSWORD}@{settings.RDS_HOST}:{settings.RDS_PORT}/{settings.RDS_DB}"

# Determine final DATABASE_URL
# Priority: 1. env DATABASE_URL, 2. RDS (if RDS_HOST is set to something other than localhost), 3. SQLite
DATABASE_URL = settings.DATABASE_URL

# Function to test database connection
def test_connection(url):
    try:
        temp_engine = create_engine(url, connect_args={"connect_timeout": 3})
        with temp_engine.connect() as conn:
            return True
    except Exception as e:
        print(f"⚠️  Connection check failed for {url.split('@')[-1] if '@' in url else url}: {e}")
        return False

# Logic to choose database with fallback
if not DATABASE_URL or DATABASE_URL == "sqlite:///farmfreeze.db":
    # If RDS_HOST is not localhost, it means we have a remote RDS configured
    if settings.RDS_HOST != "localhost" or settings.RDS_PASSWORD:
        print(f"🔄 Attempting to connect to RDS at {settings.RDS_HOST}...")
        if test_connection(RDS_URL):
            DATABASE_URL = RDS_URL
            print(f"✅ Successfully connected to RDS Database at {settings.RDS_HOST}")
        else:
            DATABASE_URL = SQLITE_URL
            print(f"❌ RDS Unreachable. Falling back to local SQLite: {SQLITE_DB_PATH}")
    else:
        DATABASE_URL = SQLITE_URL
        print(f"📦 Using local SQLite fallback: {SQLITE_DB_PATH}")
else:
    print(f"🔗 Using explicit DATABASE_URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

# SQLAlchemy Engine Configuration
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
else:
    # Set connection timeout for RDS (PostgreSQL) to fail faster
    connect_args = {"connect_timeout": 10}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
