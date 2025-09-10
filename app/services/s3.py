from botocore.exceptions import ClientError
from app.core.config import settings
import logging
from typing import Dict, Optional, Any
import os
from datetime import datetime, timezone
from fastapi import HTTPException
import boto3

logger = logging.getLogger(__name__)


class S3Service:
    """Service for interacting with AWS S3."""

    def __init__(self):
        """Initialize the S3 service with AWS credentials from settings."""
        self.access_key = settings.aws_access_key_id
        self.secret_key = settings.aws_secret_access_key
        self.region = settings.aws_region
        self.bucket_name = settings.aws_bucket_name
        self.expiration = settings.aws_presigned_url_expiration

    def get_s3_client(self) -> Any:
        """Get configured S3 client"""
        session = boto3.Session()
        return session.client(
            's3',
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=settings.aws_endpoint_url,
        )

    async def get_presigned_upload_url(
        self,
        file_name: str,
        prefix: Optional[str] = None,
        content_type: Optional[str] = None,
        is_public: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a pre-signed URL for uploading a file to S3 using PutObject.
        """
        try:
            # Validate inputs
            if not file_name:
                raise HTTPException(status_code=400, detail="File name is required")
            if not content_type:
                raise HTTPException(status_code=400, detail="Content type is required")

            # Generate object key
            extension = content_type.split("/")[-1]
            timestamp = int(datetime.now(timezone.utc).timestamp() * 1000)
            key = f"{prefix}/{timestamp}-{file_name}"

            # Initialize S3 client
            s3_client = self.get_s3_client()

            # Generate pre-signed URL
            presigned_url = s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=self.expiration,
            )

            logger.info(f"Generated pre-signed URL for key: {key}")
            return {
                "presigned_url": presigned_url,
                "key": key,
                "file_url": f"https://{self.bucket_name}.s3.{self.region}.amazonaws.com/{key}",
                "expires_in": self.expiration
            }

        except ClientError as e:
            logger.error(f"AWS Error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate pre-signed URL: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def confirm_upload(self, key: str, etag: Optional[str] = None) -> Dict[str, Any]:
        """
        Confirm that a file has been uploaded to S3 and get its metadata.

        Args:
            key: The S3 key of the uploaded file
            etag: Optional ETag to verify the upload

        Returns:
            Dictionary containing file information
        """
        try:
            # Use boto3 directly for consistency with get_presigned_upload_url
            s3_client = self.get_s3_client()

            # Check if the file exists and get its metadata
            response = s3_client.head_object(Bucket=self.bucket_name, Key=key)

            # Verify ETag if provided
            if etag and response.get('ETag', '').strip('"') != etag.strip('"'):
                return {
                    "key": key,
                    "success": False,
                    "error": "ETag mismatch, upload may be incomplete"
                }

            # Return file information
            return {
                "key": key,
                "success": True,
                "file_info": {
                    "key": key,
                    "size": response.get('ContentLength', 0),
                    "etag": response.get('ETag', '').strip('"'),
                    "last_modified": response.get('LastModified', '').isoformat() if response.get('LastModified') else None,
                    "content_type": response.get('ContentType', 'application/octet-stream')
                },
                "error": ""
            }

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey' or error_code == '404':
                return {
                    "key": key,
                    "success": False,
                    "error": "File not found, upload may have failed"
                }
            else:
                logger.error(f"Error confirming upload: {str(e)}")
                return {
                    "key": key,
                    "success": False,
                    "error": f"S3 error: {error_code}"
                }
        except Exception as e:
            logger.error(f"Error confirming upload: {str(e)}")
            return {
                "key": key,
                "success": False,
                "error": str(e)
            }

    async def get_presigned_download_url(self, key: str, expires_in: int = 900) -> str:
        """
        Generate a presigned URL for downloading a file from S3.

        Args:
            key: The S3 key of the file to download
            expires_in: Optional expiration time in seconds

        Returns:
            Presigned download URL
        """
        try:
            # Use boto3 directly for consistency
            s3_client = self.get_s3_client()

            # Generate the presigned URL
            params = {
                'Bucket': self.bucket_name,
                'Key': key
            }

            # Generate the presigned URL with proper configuration
            url = s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params=params,
                ExpiresIn=expires_in or self.expiration
            )

            logger.info(f"Generated presigned download URL for key: {key}")
            return url

        except ClientError as e:
            logger.error(f"AWS Error generating presigned download URL: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating presigned download URL: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    async def download_file(self, key: str, local_path: str) -> bool:
        """
        Download a file from S3 to a local path.

        Args:
            key: The S3 key of the file to download
            local_path: The local path to save the file to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Use boto3 directly for consistency
            s3_client = self.get_s3_client()

            # Download the file
            s3_client.download_file(self.bucket_name, key, local_path)
            logger.info(f"Downloaded file from S3: {key} to {local_path}")

            return True

        except ClientError as e:
            logger.error(f"AWS Error downloading file: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error downloading file: {str(e)}")
            return False

    async def upload_file(self, local_path: str, key: str, content_type: Optional[str] = None, is_public: bool = False) -> bool:
        """
        Upload a file from a local path to S3.

        Args:
            local_path: The local path of the file to upload
            key: The S3 key to upload the file to
            content_type: Optional content type of the file
            is_public: Whether the file should be publicly accessible (Note: requires bucket to support ACLs)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use boto3 directly for consistency
            s3_client = self.get_s3_client()

            # Set up extra args
            extra_args = {}

            if content_type:
                extra_args['ContentType'] = content_type
            else:
                # Try to guess content type from file extension
                import mimetypes
                content_type, _ = mimetypes.guess_type(local_path)
                if content_type:
                    extra_args['ContentType'] = content_type

            # First try without ACL since many buckets have ACLs disabled
            try:
                # Upload the file without ACL
                s3_client.upload_file(
                    local_path,
                    self.bucket_name,
                    key,
                    ExtraArgs=extra_args
                )

                logger.info(f"Uploaded file to S3 without ACL: {local_path} -> {key}")
                return True

            except ClientError as e:
                # If the error is not related to ACL, re-raise it
                if 'AccessControlList' not in str(e):
                    raise

                # If we get here, the bucket might support ACLs, so try with ACL if requested
                if is_public:
                    logger.info(f"Retrying upload with ACL for {key}")
                    # Only try with ACL if is_public is True
                    extra_args['ACL'] = 'public-read'
                    s3_client.upload_file(
                        local_path,
                        self.bucket_name,
                        key,
                        ExtraArgs=extra_args
                    )
                    logger.info(f"Uploaded file to S3 with public-read ACL: {local_path} -> {key}")
                    return True
                else:
                    # If not public, re-raise the original error
                    raise

        except ClientError as e:
            logger.error(f"AWS Error uploading file: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
            return False

    async def delete_file(self, key: str) -> bool:
        """
        Delete a file from S3.

        Args:
            key: The S3 key of the file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            # Use boto3 directly for consistency
            s3_client = self.get_s3_client()

            # Delete the file
            s3_client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"Deleted file from S3: {key}")

            return True

        except ClientError as e:
            logger.error(f"AWS Error deleting file: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error deleting file: {str(e)}")
            return False

    async def check_file_exists(self, key: str) -> bool:
        """
        Check if a file exists in S3.

        Args:
            key: The S3 key of the file to check

        Returns:
            True if the file exists, False otherwise
        """
        try:
            # Use boto3 directly for consistency
            s3_client = self.get_s3_client()

            # Check if the file exists
            s3_client.head_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"File exists in S3: {key}")

            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'NoSuchKey' or error_code == '404':
                logger.info(f"File does not exist in S3: {key}")
                return False
            else:
                logger.error(f"AWS Error checking if file exists: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Error checking if file exists: {str(e)}")
        except Exception as e:
            logger.error(f"Error checking if file exists: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")


# Create a singleton instance
s3_service = S3Service()
