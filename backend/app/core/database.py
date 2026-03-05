from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

# AWS Aurora PostgreSQL Configuration
RDS_USER = os.getenv("RDS_USER", "postgres")
RDS_PASSWORD = os.getenv("RDS_PASSWORD", "")
RDS_HOST = os.getenv("RDS_HOST", "localhost")
RDS_PORT = os.getenv("RDS_PORT", "5432")
RDS_DB = os.getenv("RDS_DB", "farmfreeze")

# SQLite Fallback Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLITE_DB_PATH = os.path.join(BASE_DIR, "farmfreeze.db")
SQLITE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# RDS URL construction
RDS_URL = f"postgresql://{RDS_USER}:{RDS_PASSWORD}@{RDS_HOST}:{RDS_PORT}/{RDS_DB}"

# Determine final DATABASE_URL
# Priority: 1. env DATABASE_URL, 2. RDS (if RDS_HOST is set to something other than localhost), 3. SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # If RDS_HOST is not localhost, it means we have a remote RDS configured
    if RDS_HOST != "localhost" or RDS_PASSWORD:
        DATABASE_URL = RDS_URL
        print(f"📡 Using RDS Database at {RDS_HOST}")
    else:
        DATABASE_URL = SQLITE_URL
        print(f"📦 Using local SQLite fallback: {SQLITE_DB_PATH}")
else:
    print(f"🔗 Using explicit DATABASE_URL: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

# SQLAlchemy Engine Configuration
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
