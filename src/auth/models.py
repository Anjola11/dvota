"""Database models for authentication and user management.

This module defines SQLModel classes representing database tables for
users (planners and vendors) and OTP records. Uses PostgreSQL-specific
types (JSONB, TIMESTAMP) for rich data storage and timezone support.
"""

from sqlmodel import SQLModel, Field, Column
import uuid
from datetime import datetime, timezone, timedelta
import sqlalchemy.dialects.postgresql as pg
from typing import Optional, List, Dict
from enum import Enum

def utc_now():
    """Generate current UTC timestamp.
    
    Provides timezone-aware datetime for model default values.
    Ensures consistent timestamp handling across the application.
    
    Returns:
        datetime: Current UTC time with timezone information.
    """
    return datetime.now(timezone.utc)


class User(SQLModel, table=True):
    __tablename__ = "users"
    
    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    fullName: str
    email: str = Field(unique=True, index=True)
    password_hash: str
    email_verified: bool = False
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )

def get_expiry_time(minutes):
    """Generate OTP expiration timestamp.
    """
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)

class SignupOtp(SQLModel, table=True):
   
    __tablename__ = "signupOtp"
    
    otp_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    otp: str
    user_id: uuid.UUID
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True)))
    expires: datetime = Field(
        default_factory=lambda: get_expiry_time(10),
        sa_column=Column(pg.TIMESTAMP(timezone=True)))

class ForgotPasswordOtp(SQLModel, table=True):
    """Password reset OTP records table.
    
    Stores one-time passwords sent to users for password reset
    workflows. Records expire after 10 minutes for security.
    
    Attributes:
        otp_id: Primary key, auto-generated UUID.
        otp: The verification code (6-digit numeric string).
        user_id: Reference to user requesting password reset (not a foreign key).
        created_at: OTP generation timestamp (UTC).
        expires: Expiration timestamp (10 minutes after creation).
    """
    __tablename__ = "forgotPasswordOtp"
    
    otp_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    otp: str
    user_id: uuid.UUID
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True)))
    expires: datetime = Field(
        default_factory=lambda: get_expiry_time(10),
        sa_column=Column(pg.TIMESTAMP(timezone=True)))

