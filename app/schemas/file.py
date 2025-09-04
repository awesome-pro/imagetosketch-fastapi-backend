from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any, List
import os
from app.core.config import settings


class GetPresignedUploadUrlRequest(BaseModel):
    """Request model for getting a presigned upload URL."""
    file_name: str = Field(..., description="Name of the file to upload")
    prefix: Optional[str] = Field(None, description="Optional prefix (folder) for the file")
    file_type: Optional[str] = Field(None, description="Content type of the file")
    is_public: Optional[bool] = Field(False, description="Whether the file should be publicly accessible")

    @field_validator('file_name')
    def validate_file_name(cls, v):
        """Validate the file name."""
        # Check if file extension is allowed
        ext = os.path.splitext(v)[1].lower().lstrip('.')
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise ValueError(f"File extension '{ext}' is not allowed. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}")
        return v


class GetPresignedUploadUrlResponse(BaseModel):
    """Response model for getting a presigned upload URL."""
    presigned_url: str = Field(..., description="Presigned URL for uploading the file")
    key: str = Field(..., description="S3 key for the uploaded file")
    file_url: str = Field(..., description="URL of the uploaded file")
    expires_in: int = Field(..., description="Expiration time of the presigned URL")


class ConfirmFileUploadRequest(BaseModel):
    """Request model for confirming a file upload."""
    key: str = Field(..., description="S3 key of the uploaded file")
    etag: Optional[str] = Field(None, description="ETag of the uploaded file")


class FileInfo(BaseModel):
    """Model for file information."""
    key: str = Field(..., description="S3 key of the file")
    size: int = Field(..., description="Size of the file in bytes")
    etag: str = Field(..., description="ETag of the file")


class ConfirmFileUploadResponse(BaseModel):
    """Response model for confirming a file upload."""
    key: str = Field(..., description="S3 key of the uploaded file")
    success: bool = Field(..., description="Whether the confirmation was successful")
    file_info: Optional[FileInfo] = Field(None, description="Information about the uploaded file")
    error: str = Field("", description="Error message if the confirmation failed")


class ProcessImageRequest(BaseModel):
    """Request model for processing an image."""
    input_key: str = Field(..., description="S3 key of the input image")
    method: str = Field("advanced", description="Sketch method to use (basic, advanced, or artistic)")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional configuration parameters")

    @field_validator('method')
    def validate_method(cls, v):
        """Validate the sketch method."""
        if v not in settings.SKETCH_METHODS:
            raise ValueError(f"Invalid sketch method: {v}. Allowed methods: {', '.join(settings.SKETCH_METHODS)}")
        return v


class ProcessImageResponse(BaseModel):
    """Response model for processing an image."""
    success: bool = Field(..., description="Whether the processing was successful")
    input_key: Optional[str] = Field(None, description="S3 key of the input image")
    output_key: Optional[str] = Field(None, description="S3 key of the processed image")
    method: Optional[str] = Field(None, description="Sketch method used")
    download_url: Optional[str] = Field(None, description="Presigned URL for downloading the processed image")
    error: Optional[str] = Field(None, description="Error message if the processing failed")


class BatchProcessRequest(BaseModel):
    """Request model for batch processing images."""
    input_keys: List[str] = Field(..., description="List of S3 keys for input images")
    method: str = Field("advanced", description="Sketch method to use (basic, advanced, or artistic)")
    config: Optional[Dict[str, Any]] = Field(None, description="Optional configuration parameters")
    max_concurrency: Optional[int] = Field(5, description="Maximum number of concurrent conversions")

    @field_validator('method')
    def validate_method(cls, v):
        """Validate the sketch method."""
        if v not in settings.SKETCH_METHODS:
            raise ValueError(f"Invalid sketch method: {v}. Allowed methods: {', '.join(settings.SKETCH_METHODS)}")
        return v

    @field_validator('max_concurrency')
    def validate_max_concurrency(cls, v):
        """Validate the maximum concurrency."""
        if v < 1:
            raise ValueError("Maximum concurrency must be at least 1")
        if v > 20:
            raise ValueError("Maximum concurrency cannot exceed 20")
        return v


class BatchProcessResponse(BaseModel):
    """Response model for batch processing images."""
    success: bool = Field(..., description="Whether the batch processing was successful")
    total: int = Field(..., description="Total number of images processed")
    successful: int = Field(..., description="Number of images successfully processed")
    failed: int = Field(..., description="Number of images that failed to process")
    results: List[ProcessImageResponse] = Field(..., description="Results for each processed image")
