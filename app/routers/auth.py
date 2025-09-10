from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db_session
from app.schemas.user import GoogleOAuthCallback, GoogleOAuthRequest, GoogleOAuthURL, UserCreate, UserLogin, UserResponse
from app.services.auth import AuthService
from app.core.deps import get_current_active_user
from app.core.config import settings
from app.services.google_oauth import GoogleOAuthService
from app.utils.cookies import set_auth_cookie

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/sign-up", response_model=UserResponse, status_code=status.HTTP_201_CREATED,)
async def register(
    user_data: UserCreate,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
):
    """Register a new user."""
    user = await AuthService.create_user(db, user_data)
    access_token = AuthService.create_user_token(user)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
        httponly=True,
        secure=not settings.debug,
        samesite="lax"
    )
    return user


@router.post("/sign-in", response_model=UserResponse)
async def login(
    login_data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db_session)
):
    """Login user and set access token in cookie."""
    user = await AuthService.authenticate_user(db, login_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    
    access_token = AuthService.create_user_token(user)
    
    # Set cookie with proper security settings
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,  # Convert to seconds
        httponly=True,  # Prevent XSS attacks
        secure=not settings.debug,  # Use secure in production
        samesite="lax"  # CSRF protection
    )
    
    return user


@router.post("/sign-out")
async def logout(response: Response):
    """Logout user by clearing the access token cookie."""
    response.delete_cookie(key="access_token")
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user = Depends(get_current_active_user)
):
    """Get current user information."""
    return current_user

# Google OAuth endpoints
@router.get("/google/url", response_model=GoogleOAuthURL)
async def get_google_oauth_url():
    """Get Google OAuth authorization URL."""
    auth_url = await GoogleOAuthService.get_google_oauth_url()
    return GoogleOAuthURL(auth_url=auth_url)


@router.post("/google/callback", response_model=UserResponse)
async def google_oauth_callback(
    callback_data: GoogleOAuthCallback,
    response: Response,
    db: AsyncSession = Depends(get_db_session)
):
    """Handle Google OAuth callback with authorization code."""
    try:
        # Exchange code for tokens
        tokens = await GoogleOAuthService.exchange_code_for_tokens(callback_data.code)
        
        # Get user info using access token
        google_user_info = await GoogleOAuthService.get_google_user_info(tokens['access_token'])
        
        # Add Google ID to user info
        google_user_info['google_id'] = google_user_info['id']
        
        # Find or create user
        user = await GoogleOAuthService.find_or_create_oauth_user(db, google_user_info)
        
        # Create JWT token
        access_token = AuthService.create_user_token(user)
        
        # Set cookie with proper cross-domain configuration
        set_auth_cookie(response, access_token)
        
        return user
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )


@router.post("/google/verify", response_model=UserResponse)
async def google_oauth_verify(
    oauth_request: GoogleOAuthRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session)
):
    """Verify Google ID token and authenticate user."""
    try:
        # Verify ID token
        google_user_info = await GoogleOAuthService.verify_google_token(oauth_request.id_token)
        
        # Find or create user
        user = await GoogleOAuthService.find_or_create_oauth_user(db, google_user_info)
        
        # Create JWT token
        access_token = AuthService.create_user_token(user)
        
        # Set cookie with proper cross-domain configuration
        set_auth_cookie(response, access_token)
        
        return user
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )