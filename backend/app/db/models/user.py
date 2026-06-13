"""
User Model - Phase 1
For authentication and API key management
"""
from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User table for authentication"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    
    # API Key for programmatic access
    api_key_hash = Column(String(64), nullable=True, unique=True, index=True)
    
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
