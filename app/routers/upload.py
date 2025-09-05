from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db_session
from app.core.deps import get_current_active_user
from app.services.s3 import s3_service
from app.core.config import settings
from app.models.user import User
from typing import Dict, Any
import uuid

router = APIRouter(prefix="/upload", tags=["File Upload"])


@router.post("/presigned-url")
async def get_presigned_upload_url(
    filename: str,
    content_type: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get a presigned URL for direct upload to S3."""

    # Validate content type
    if content_type not in settings.allowed_file_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {content_type} not allowed. Allowed types: {settings.allowed_file_types}"
        )

    # Generate unique filename with user prefix
    file_extension = filename.split('.')[-1] if '.' in filename else 'jpg'
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    prefix = f"uploads/{current_user.id}"

    try:
        result = await s3_service.get_presigned_upload_url(
            file_name=unique_filename,
            prefix=prefix,
            content_type=content_type
        )

        return {
            "presigned_url": result["presigned_url"],
            "key": result["key"],
            "file_url": result["file_url"],
            "expires_in": result["expires_in"]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate presigned URL: {str(e)}"
        )


@router.post("/confirm")
async def confirm_upload(
    key: str,
    etag: str = None,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Confirm that a file has been uploaded successfully."""

    # Verify the key belongs to the current user
    if not key.startswith(f"uploads/{current_user.id}/"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only confirm uploads for your own files"
        )

    try:
        result = await s3_service.confirm_upload(key, etag)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        return {
            "success": True,
            "message": "Upload confirmed successfully",
            "file_info": result["file_info"]
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm upload: {str(e)}"
        )


@router.get("/download-url/{key:path}")
async def get_download_url(
    key: str,
    current_user: User = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """Get a presigned download URL for a file."""

    # Verify the key belongs to the current user or is a processed sketch
    user_prefix = f"uploads/{current_user.id}/"
    sketch_prefix = f"sketches/{current_user.id}/"

    # if not (key.startswith(user_prefix) or key.startswith(sketch_prefix)):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="You can only access your own files"
    #     )

    try:
        # Check if file exists
        if not await s3_service.check_file_exists(key):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        download_url = await s3_service.get_presigned_download_url(key)

        return {
            "download_url": download_url,
            "key": key,
            "expires_in": 900  # 15 minutes
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )
