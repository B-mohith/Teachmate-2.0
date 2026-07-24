from datetime import datetime, timezone
import uuid
from typing import List

from sqlalchemy import String, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class User(Base):
    __tablename__ = "users"

    # Primary Key using native PostgreSQL UUIDs
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    email: Mapped[str] = mapped_column(
        String(255), 
        unique=True, 
        index=True, 
        nullable=False
    )
    
    hashed_password: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )

    # Relationship: A user can have many courses
    courses: Mapped[List["Course"]] = relationship(
        "Course", 
        back_populates="owner", 
        cascade="all, delete-orphan"
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        primary_key=True, 
        default=uuid.uuid4
    )
    
    title: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    
    # Foreign Key pointing to the 'id' column of the 'users' table
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("users.id"), 
        nullable=False
    )

    # Relationship: Connects Course back to its User owner
    owner: Mapped["User"] = relationship(
        "User", 
        back_populates="courses"
    )