"""Pydantic request/response schemas for the LMPC Compliance System API."""
import uuid
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: uuid.UUID


class UserMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    name: str
    email: str
    role: str
    region: Optional[str] = None


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Literal["Inspector", "Reviewer", "Admin"]
    region: Optional[str] = None


class RegisterResponse(BaseModel):
    user_id: uuid.UUID
