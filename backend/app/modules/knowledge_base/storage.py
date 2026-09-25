"""
Storage providers for knowledge base documents.
Supports S3-compatible storage (AWS S3, MinIO, etc.)
"""

import asyncio
import io
import logging
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional

import boto3
from botocore.exceptions import ClientError

from app.config.settings import settings

logger = logging.getLogger(__name__)


class StorageProvider(ABC):
    """Abstract base class for storage providers."""

    @abstractmethod
    async def upload_file(
        self,
        file: BinaryIO,
        path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file to storage.

        Args:
            file: File-like object to upload
            path: Destination path in storage
            content_type: MIME type of the file

        Returns:
            Storage path/URL of the uploaded file
        """
        pass

    @abstractmethod
    async def download_file(self, path: str) -> bytes:
        """
        Download a file from storage.

        Args:
            path: Path of the file in storage

        Returns:
            File contents as bytes
        """
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """
        Delete a file from storage.

        Args:
            path: Path of the file to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        pass

    @abstractmethod
    async def get_presigned_url(
        self,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Get a presigned URL for temporary access to a file.

        Args:
            path: Path of the file in storage
            expires_in: URL expiration time in seconds

        Returns:
            Presigned URL string
        """
        pass

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """
        Check if a file exists in storage.

        Args:
            path: Path of the file to check

        Returns:
            True if file exists, False otherwise
        """
        pass


class S3Storage(StorageProvider):
    """
    S3-compatible storage provider (works with AWS S3 and MinIO).
    """

    def __init__(
        self,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
    ):
        """
        Initialize S3 storage provider.

        Args:
            endpoint_url: S3 endpoint URL (for MinIO)
            access_key: AWS access key ID
            secret_key: AWS secret access key
            bucket_name: S3 bucket name
            region: AWS region
        """
        self.endpoint_url = endpoint_url or settings.S3_ENDPOINT_URL
        self.access_key = access_key or settings.S3_ACCESS_KEY
        self.secret_key = secret_key or settings.S3_SECRET_KEY
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME
        self.region = region or settings.S3_REGION

        # Initialize S3 client
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )

        # Ensure bucket exists
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Create bucket if it doesn't exist."""
        try:
            self.client.head_bucket(Bucket=self.bucket_name)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            if error_code in ("404", "NoSuchBucket"):
                logger.info(f"Creating bucket: {self.bucket_name}")
                try:
                    self.client.create_bucket(Bucket=self.bucket_name)
                except ClientError as create_error:
                    logger.error(f"Failed to create bucket: {create_error}")
            else:
                logger.warning(f"Error checking bucket: {e}")

    async def upload_file(
        self,
        file: BinaryIO,
        path: str,
        content_type: Optional[str] = None,
    ) -> str:
        """Upload a file to S3/MinIO."""

        def _upload():
            """Synchronous upload operation to run in thread pool."""
            try:
                extra_args = {}
                if content_type:
                    extra_args["ContentType"] = content_type

                self.client.upload_fileobj(
                    file,
                    self.bucket_name,
                    path,
                    ExtraArgs=extra_args if extra_args else None,
                )

                logger.info(f"Uploaded file to: {path}")
                return path
            except ClientError as e:
                logger.error(f"Failed to upload file to {path}: {e}")
                raise

        try:
            # Run blocking boto3 call in thread pool to avoid blocking event loop
            return await asyncio.to_thread(_upload)
        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    async def download_file(self, path: str) -> bytes:
        """Download a file from S3/MinIO."""

        def _download():
            """Synchronous download operation to run in thread pool."""
            try:
                response = self.client.get_object(Bucket=self.bucket_name, Key=path)
                return response["Body"].read()
            except ClientError as e:
                logger.error(f"Failed to download file from {path}: {e}")
                raise

        try:
            # Run blocking boto3 call in thread pool to avoid blocking event loop
            return await asyncio.to_thread(_download)
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise

    async def delete_file(self, path: str) -> bool:
        """Delete a file from S3/MinIO."""

        def _delete():
            """Synchronous delete operation to run in thread pool."""
            try:
                self.client.delete_object(Bucket=self.bucket_name, Key=path)
                logger.info(f"Deleted file: {path}")
                return True
            except ClientError as e:
                logger.error(f"Failed to delete file from {path}: {e}")
                return False

        try:
            # Run blocking boto3 call in thread pool to avoid blocking event loop
            return await asyncio.to_thread(_delete)
        except Exception as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    async def get_presigned_url(
        self,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """Get a presigned URL for a file."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": path},
                ExpiresIn=expires_in,
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise

    async def file_exists(self, path: str) -> bool:
        """Check if a file exists in S3/MinIO."""
        try:
            self.client.head_object(Bucket=self.bucket_name, Key=path)
            return True
        except ClientError:
            return False


# Default storage instance
def get_storage() -> StorageProvider:
    """Get the default storage provider instance."""
    return S3Storage()
