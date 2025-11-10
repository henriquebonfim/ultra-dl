"""
Google Cloud Storage Configuration

Manages GCS client initialization and configuration.
"""

import os
from typing import Optional
from google.cloud import storage
from google.oauth2 import service_account


# Global GCS client instance
_gcs_client: Optional[storage.Client] = None
_gcs_bucket: Optional[storage.Bucket] = None


def init_gcs() -> bool:
    """
    Initialize Google Cloud Storage client.
    
    Returns:
        True if initialization successful, False otherwise
    """
    global _gcs_client, _gcs_bucket
    
    try:
        # Get configuration from environment
        bucket_name = os.getenv('GCS_BUCKET_NAME')
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        
        if not bucket_name:
            print("Warning: GCS_BUCKET_NAME not set, GCS integration disabled")
            return False
        
        # Initialize client with credentials if provided
        if credentials_path and os.path.exists(credentials_path):
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            _gcs_client = storage.Client(credentials=credentials)
            print(f"GCS client initialized with service account: {credentials_path}")
        else:
            # Try to use default credentials (for GCE instances)
            try:
                _gcs_client = storage.Client()
                print("GCS client initialized with default credentials")
            except Exception as e:
                print(f"Warning: Could not initialize GCS client: {e}")
                print("GCS integration disabled - files will be served locally")
                return False
        
        # Get bucket reference
        _gcs_bucket = _gcs_client.bucket(bucket_name)
        
        # Verify bucket exists (optional check)
        try:
            if not _gcs_bucket.exists():
                print(f"Warning: GCS bucket '{bucket_name}' does not exist")
                print("Please create the bucket using Terraform or GCP Console")
                _gcs_bucket = None
                return False
        except Exception as e:
            print(f"Warning: Could not verify bucket existence: {e}")
            # Continue anyway - bucket might exist but we lack permissions to check
        
        print(f"GCS initialized successfully with bucket: {bucket_name}")
        return True
        
    except Exception as e:
        print(f"Error initializing GCS: {e}")
        _gcs_client = None
        _gcs_bucket = None
        return False


def get_gcs_client() -> Optional[storage.Client]:
    """
    Get the GCS client instance.
    
    Returns:
        GCS client or None if not initialized
    """
    return _gcs_client


def get_gcs_bucket() -> Optional[storage.Bucket]:
    """
    Get the GCS bucket instance.
    
    Returns:
        GCS bucket or None if not initialized
    """
    return _gcs_bucket


def is_gcs_enabled() -> bool:
    """
    Check if GCS integration is enabled and configured.
    
    Returns:
        True if GCS is available, False otherwise
    """
    return _gcs_client is not None and _gcs_bucket is not None


def gcs_health_check() -> bool:
    """
    Perform health check on GCS connection.
    
    Returns:
        True if GCS is healthy, False otherwise
    """
    if not is_gcs_enabled():
        return False
    
    try:
        # Try to check if bucket exists
        return _gcs_bucket.exists()
    except Exception as e:
        print(f"GCS health check failed: {e}")
        return False
