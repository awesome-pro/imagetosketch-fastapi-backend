from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional

from app.models.user import UserRole, UserStatus
from app.utils.pagination import PaginatedResponse


class UserBase(BaseModel):
    email: EmailStr
    name: Optional[str] = None


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
    id: str
    status: UserStatus
    role: UserRole
    avatar_url: Optional[str] = None
    is_oauth_user: bool = False
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfile(UserResponse):
    created_at: datetime
    updated_at: datetime
    total_sketches: Optional[int] = 0
    


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    
class UserListResponse(PaginatedResponse[UserResponse]):
    pass

class GoogleOAuthRequest(BaseModel):
    """Schema for Google OAuth token verification"""
    id_token: str


class GoogleOAuthCallback(BaseModel):
    """Schema for Google OAuth callback with authorization code"""
    code: str
    state: Optional[str] = None


class GoogleOAuthURL(BaseModel):
    """Schema for Google OAuth authorization URL response"""
    auth_url: str
