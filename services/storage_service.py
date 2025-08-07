"""
Storage service for Bunny.net CDN integration
Handles file upload, download, and deletion operations
"""

import aiohttp
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse, quote
import os
from uuid import uuid4

from core.config import settings
from utils.exceptions import AppException

logger = logging.getLogger(__name__)

class StorageService:
    """Service class for Bunny.net storage operations"""
    
    def __init__(self):
        self.api_key = settings.BUNNY_STORAGE_API_KEY
        self.storage_zone = settings.BUNNY_STORAGE_ZONE
        self.storage_endpoint = settings.BUNNY_STORAGE_ENDPOINT
        self.region = settings.BUNNY_STORAGE_REGION
        
        # Construct base URL for storage API - use direct endpoint
        self.base_url = f"https://storage.bunnycdn.com/{self.storage_zone}"
        
        # Headers for API requests
        self.headers = {
            "AccessKey": self.api_key,
            "Content-Type": "application/octet-stream"
        }
    
    async def upload_file(
        self, 
        file_content: bytes, 
        filename: str,
        content_type: str = "application/pdf",
        folder: str = "documents"
    ) -> str:
        """
        Upload file to Bunny.net storage
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type of the file
            folder: Storage folder path
            
        Returns:
            Public URL of uploaded file
            
        Raises:
            AppException: If upload fails
        """
        try:
            # Generate unique filename to prevent conflicts
            file_extension = os.path.splitext(filename)[1]
            unique_filename = f"{uuid4()}{file_extension}"
            storage_path = f"{folder}/{unique_filename}"
            
            # Construct upload URL
            upload_url = f"{self.base_url}/{storage_path}"
            
            # Upload headers
            upload_headers = self.headers.copy()
            upload_headers["Content-Type"] = content_type
            
            # Upload to Bunny.net
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.put(
                    upload_url,
                    data=file_content,
                    headers=upload_headers
                ) as response:
                    
                    if response.status not in [200, 201]:
                        error_text = await response.text()
                        logger.error(f"Bunny.net upload failed: {response.status} - {error_text}")
                        raise AppException(
                            message="Failed to upload file to storage",
                            detail=f"Storage API returned {response.status}: {error_text}",
                            error_code="STORAGE_UPLOAD_FAILED"
                        )
            
            # Return the actual public CDN URL where file is accessible
            # Bunny.net storage zone "mevzuatgpt" is accessible via cdn.mevzuatgpt.org
            public_url = f"https://cdn.mevzuatgpt.org/{storage_path}"
            
            logger.info(f"File uploaded successfully: {filename} -> {unique_filename}")
            
            return public_url

            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error during upload: {str(e)}")
            raise AppException(
                message="Network error during file upload",
                detail=str(e),
                error_code="STORAGE_NETWORK_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error during upload: {str(e)}")
            raise AppException(
                message="Failed to upload file",
                detail=str(e),
                error_code="STORAGE_UPLOAD_ERROR"
            )
    
    async def download_file(self, file_url: str) -> bytes:
        """
        Download file from Bunny.net storage
        
        Args:
            file_url: Public URL of the file
            
        Returns:
            File content as bytes
            
        Raises:
            AppException: If download fails
        """
        try:
            # Extract storage path from URL
            parsed_url = urlparse(file_url)
            storage_path = parsed_url.path.lstrip('/')
            
            # For downloads, we need to use the storage API endpoint, not the CDN
            # But first check if this is already a CDN URL that needs conversion
            if "cdn.mevzuatgpt.org" in file_url:
                # Convert CDN URL back to storage API URL for download
                download_url = f"{self.base_url}/{storage_path}"
            else:
                # Use the URL as-is for storage API
                download_url = f"{self.base_url}/{storage_path}"
            
            # Download headers (without Content-Type)
            download_headers = {
                "AccessKey": self.api_key
            }
            
            # Perform download
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    download_url,
                    headers=download_headers,
                    timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Bunny.net download failed: {response.status} - {error_text}")
                        raise AppException(
                            message="Failed to download file from storage",
                            detail=f"Storage API returned {response.status}: {error_text}",
                            error_code="STORAGE_DOWNLOAD_FAILED"
                        )
                    
                    file_content = await response.read()
                    
            logger.info(f"File downloaded successfully: {file_url}")
            
            return file_content
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error during download: {str(e)}")
            raise AppException(
                message="Network error during file download",
                detail=str(e),
                error_code="STORAGE_NETWORK_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error during download: {str(e)}")
            raise AppException(
                message="Failed to download file",
                detail=str(e),
                error_code="STORAGE_DOWNLOAD_ERROR"
            )
    
    async def delete_file(self, file_url: str) -> bool:
        """
        Delete file from Bunny.net storage
        
        Args:
            file_url: Public URL of the file
            
        Returns:
            True if deletion successful
            
        Raises:
            AppException: If deletion fails
        """
        try:
            # Extract storage path from URL
            parsed_url = urlparse(file_url)
            storage_path = parsed_url.path.lstrip('/')
            
            # Construct delete URL
            delete_url = f"{self.base_url}/{storage_path}"
            
            # Delete headers
            delete_headers = {
                "AccessKey": self.api_key
            }
            
            # Perform deletion
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    delete_url,
                    headers=delete_headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status not in [200, 404]:  # 404 means already deleted
                        error_text = await response.text()
                        logger.error(f"Bunny.net deletion failed: {response.status} - {error_text}")
                        raise AppException(
                            message="Failed to delete file from storage",
                            detail=f"Storage API returned {response.status}: {error_text}",
                            error_code="STORAGE_DELETE_FAILED"
                        )
            
            logger.info(f"File deleted successfully: {file_url}")
            return True
            
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error during deletion: {str(e)}")
            raise AppException(
                message="Network error during file deletion",
                detail=str(e),
                error_code="STORAGE_NETWORK_ERROR"
            )
        except Exception as e:
            logger.error(f"Unexpected error during deletion: {str(e)}")
            raise AppException(
                message="Failed to delete file",
                detail=str(e),
                error_code="STORAGE_DELETE_ERROR"
            )
    
    async def get_file_info(self, file_url: str) -> Optional[Dict[str, Any]]:
        """
        Get file information from Bunny.net storage
        
        Args:
            file_url: Public URL of the file
            
        Returns:
            Dictionary with file information or None if not found
        """
        try:
            # Extract storage path from URL
            parsed_url = urlparse(file_url)
            storage_path = parsed_url.path.lstrip('/')
            
            # Construct info URL
            info_url = f"{self.base_url}/{storage_path}"
            
            # Info headers
            info_headers = {
                "AccessKey": self.api_key
            }
            
            # Get file info using HEAD request
            async with aiohttp.ClientSession() as session:
                async with session.head(
                    info_url,
                    headers=info_headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    
                    if response.status == 404:
                        return None
                    
                    if response.status != 200:
                        logger.error(f"Failed to get file info: {response.status}")
                        return None
                    
                    # Extract file information from headers
                    file_info = {
                        "size": int(response.headers.get("Content-Length", 0)),
                        "content_type": response.headers.get("Content-Type", "application/octet-stream"),
                        "last_modified": response.headers.get("Last-Modified"),
                        "etag": response.headers.get("ETag")
                    }
                    
            return file_info
            
        except Exception as e:
            logger.error(f"Error getting file info: {str(e)}")
            return None
    
    async def validate_storage_connection(self) -> bool:
        """
        Validate connection to Bunny.net storage
        
        Returns:
            True if connection is valid
        """
        try:
            # Test connection by listing storage zone root
            test_url = self.base_url
            
            headers = {
                "AccessKey": self.api_key
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    test_url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    
                    # Any response (even 404) indicates valid connection
                    if response.status in [200, 404]:
                        logger.info("Bunny.net storage connection validated")
                        return True
                    
                    logger.error(f"Storage validation failed: {response.status}")
                    return False
                    
        except Exception as e:
            logger.error(f"Storage validation error: {str(e)}")
            return False
