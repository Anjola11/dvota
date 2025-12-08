"""Pydantic schemas for authentication API.

This module defines the request and response models used in authentication
endpoints. Validates data for the simplified, single-user-table architecture.
"""

from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid
from typing import Optional
from src.emailServices.schemas import OtpTypes

# --- INPUT SCHEMAS ---

class UserInput(BaseModel):
    """Payload for user registration."""
    fullName: str
    email: EmailStr
    password: str

class LoginInput(BaseModel):
    """Payload for user login."""
    email: EmailStr
    password: str

class VerifyOtpInput(BaseModel):
    """Payload for verifying email/password OTPs."""
    user_id: uuid.UUID
    otp: str
    otp_type: OtpTypes

class ForgotPasswordInput(BaseModel):
    """Payload for initiating password reset."""
    email: EmailStr

class ResetPasswordInput(BaseModel):
    """Payload for completing password reset."""
    new_password: str
    token: str

# --- OUTPUT/RESPONSE SCHEMAS ---

class User(BaseModel):
    """Base user model for responses (excludes sensitive data)."""
    user_id: uuid.UUID 
    fullName: str
    email: EmailStr 
    email_verified: bool 
    created_at: datetime 

class UserCreateResponse(BaseModel):
    """Response structure for successful signup."""
    success: bool
    message: str
    data: User

class LoginData(BaseModel):
    """Data returned upon successful login."""
    user_id: uuid.UUID
    fullName: str
    email: EmailStr
    email_verified: bool
    created_at: datetime
    access_token: str
    refresh_token: str

class LoginResponse(BaseModel):
    """Response structure for successful login."""
    success: bool
    message: str
    data: LoginData

class ForgotPasswordResponse(BaseModel):
    """Response structure for forgot password request."""
    success: bool
    message: str
    data: dict = {}

class ResetPasswordInput(BaseModel):
    new_password: str
    reset_token: str
 
class RenewAccessTokenInput(BaseModel):
    refresh_token: str

class RenewAccessTokenResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}