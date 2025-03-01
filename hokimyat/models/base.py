from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=True)
    username = Column(String, nullable=True)
    phone_number = Column(String, unique=True)
    full_name = Column(String)
    job_title = Column(String)
    mahalla_id = Column(Integer, ForeignKey('mahallas.id'))
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    mahalla = relationship("Mahalla", back_populates="users")

class Mahalla(Base):
    __tablename__ = 'mahallas'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    users = relationship("User", back_populates="mahalla")

class Channel(Base):
    __tablename__ = 'channels'
    
    id = Column(Integer, primary_key=True)
    channel_id = Column(String, unique=True)
    username = Column(String)