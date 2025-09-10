from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db_session
from app.core.security import verify_token
from app.services.auth import AuthService
from app.models.user import User, UserStatus
from typing import Optional


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> User:
    """Get current authenticated user from cookie."""
    token = request.cookies.get("access_token")
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    
    try:
        payload = verify_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
            )
        
    except ValueError:
        print("Exception in get_current_user: Invalid user ID format")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )
    except Exception as e:
        print("Exception in get_current_user", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )
    
    user = await AuthService.get_user_by_id(db, user_id=user_id)
    if user is None:
        print("User not found in get_current_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Get current active user."""
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


async def get_optional_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    token = request.cookies.get("access_token")
    
    if not token:
        return None
    
    try:
        payload = verify_token(token)
        user_id: str | None = payload.get("sub")
        if user_id is None:
            return None
        
        user = await AuthService.get_user_by_id(db, user_id=user_id)
        return user
    except (ValueError, Exception):
        return None
