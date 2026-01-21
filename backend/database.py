"""
Database configuration and models for ReelCall
"""

import os
from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import create_engine, Column, String, Text, Integer, DateTime, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create engine
engine = create_engine(DATABASE_URL)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Embedding dimension for all-MiniLM-L6-v2
EMBEDDING_DIMENSION = 384


class Reel(Base):
    """Reel model representing a saved Instagram reel"""
    __tablename__ = "reels"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    url = Column(String, unique=True, nullable=False)
    
    # AI Generated Content
    transcript = Column(Text)
    summary = Column(Text)
    tags = Column(ARRAY(String))
    category = Column(String)
    
    # Embedding for RAG (384 dimensions for all-MiniLM-L6-v2)
    embedding = Column(Vector(EMBEDDING_DIMENSION))
    
    # Metadata
    duration_seconds = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert model to dictionary for JSON serialization"""
        return {
            "id": str(self.id),
            "url": self.url,
            "transcript": self.transcript,
            "summary": self.summary,
            "tags": self.tags or [],
            "category": self.category,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
