from datetime import datetime
import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict


# ==========================================
# USER SCHEMAS
# ==========================================

class UserCreate(BaseModel):
    """Schema for incoming registration requests."""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for outgoing user data (excludes passwords!)."""
    id: uuid.UUID
    email: EmailStr
    created_at: datetime

    # Tells Pydantic to read data directly from SQLAlchemy ORM models
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# COURSE SCHEMAS
# ==========================================

class CourseBase(BaseModel):
    """Shared fields across all Course schemas."""
    title: str


class CourseCreate(CourseBase):
    """Schema for incoming course creation requests."""
    pass  # Inherits title and description from CourseBase


class CourseResponse(CourseBase):
    """Schema for outgoing course responses."""
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)