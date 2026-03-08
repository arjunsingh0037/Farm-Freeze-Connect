"""
Configuration settings for FarmFreeze Connect
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    """Application settings"""
    
    # App Configuration
    APP_NAME: str = "FarmFreeze Connect API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # RDS Configuration (for reference/manual use)
    RDS_USER: str = os.getenv("RDS_USER", "postgres")
    RDS_PASSWORD: str = os.getenv("RDS_PASSWORD", "")
    RDS_HOST: str = os.getenv("RDS_HOST", "localhost")
    RDS_PORT: str = os.getenv("RDS_PORT", "5432")
    RDS_DB: str = os.getenv("RDS_DB", "farmfreeze")
    
    # AWS Configuration
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    
    # AWS AI Services
    BEDROCK_MODEL_ID: str = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-v2")
    
    # SNS Configuration
    SNS_TOPIC_ARN: str = os.getenv("SNS_TOPIC_ARN", "")
    
    # Extra Services
    CLAUDE_API_KEY: str = os.getenv("CLAUDE_API_KEY", "")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "farmfreeze-voice-uploads")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"


settings = Settings()