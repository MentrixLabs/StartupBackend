from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Boolean, Date, BigInteger, ForeignKey, Enum, Float, Text
from sqlalchemy.orm import relationship
from db.db import Base

from db.ozon.models import PaymentTransaction


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    tg_id = Column(BigInteger, unique=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    payments = relationship("PaymentTransaction", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    date_of_birth = Column(Date)
    region = Column(String)
    sex = Column(Boolean, nullable = True)
    
    api_key_ozon = Column(String, unique=True)
    client_id_ozon = Column(Integer, unique=True)
    provider_id = Column(Integer, nullable=True)