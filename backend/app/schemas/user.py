from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str | None
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
