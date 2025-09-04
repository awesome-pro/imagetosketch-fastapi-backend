from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, List

from app.models.user import UserRole, UserStatus


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=100)
    role: UserRole = Field(default=UserRole.USER)

class UserUpdate(UserBase):
    password: Optional[str] = None
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(UserBase):
    id: int
    status: UserStatus
    role: UserRole
    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    created_at: datetime
    updated_at: datetime
    total_sketches: Optional[int] = 0
    


class Token(BaseModel):
    access_token: str


class TokenData(BaseModel):
    id: Optional[int] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None

class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    limit: int
    