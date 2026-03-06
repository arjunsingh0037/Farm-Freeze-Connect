from sqlalchemy import Column, Integer, String, Float, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import date
from ..core.database import Base

class ColdStorage(Base):
    __tablename__ = "cold_storages"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500), nullable=False)
    location_lat = Column(Float, nullable=False)
    location_lng = Column(Float, nullable=False)
    total_capacity_kg = Column(Float, nullable=False)
    price_per_kg_per_day = Column(Float, nullable=False)
    storage_type = Column(String(50), default="multi-commodity")
    supported_crops = Column(String(500), default="all")  # Comma-separated: "tomato,potato,onion"
    
    bookings = relationship("Booking", back_populates="cold_storage")
    daily_capacity = relationship("DailyCapacity", back_populates="cold_storage")

class Farmer(Base):
    __tablename__ = "farmers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(15), unique=True, nullable=False)
    village = Column(String(255), nullable=True)
    district = Column(String(100), nullable=True)
    
    bookings = relationship("Booking", back_populates="farmer")

class Booking(Base):
    __tablename__ = "bookings"
    
    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(String(20), unique=True, nullable=False)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=False)
    cold_storage_id = Column(Integer, ForeignKey("cold_storages.id"), nullable=False)
    quantity_kg = Column(Float, nullable=False)
    booking_date = Column(Date, nullable=False)
    duration_days = Column(Integer, default=1)
    total_cost = Column(Float, nullable=False)
    status = Column(String(20), default="confirmed")
    crop_type = Column(String(100), nullable=True)
    
    farmer = relationship("Farmer", back_populates="bookings")
    cold_storage = relationship("ColdStorage", back_populates="bookings")

class DailyCapacity(Base):
    __tablename__ = "daily_capacity"
    
    id = Column(Integer, primary_key=True, index=True)
    cold_storage_id = Column(Integer, ForeignKey("cold_storages.id"), nullable=False)
    usage_date = Column(Date, nullable=False)
    used_capacity_kg = Column(Float, default=0.0)
    
    cold_storage = relationship("ColdStorage", back_populates="daily_capacity")

class InteractionLog(Base):
    __tablename__ = "interaction_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("farmers.id"), nullable=True)
    interaction_type = Column(String(20), default="voice") # "voice" or "text"
    query_text = Column(String(1000), nullable=False)
    extracted_intent = Column(String(2000), nullable=True) # JSON string
    s3_voice_uri = Column(String(500), nullable=True)
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    timestamp = Column(Date, default=date.today)
