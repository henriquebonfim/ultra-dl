"""
Signed URL Service

Service for generating time-limited signed URLs for secure file access.
This implementation provides token-based access control with expiration.
"""

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional


@dataclass
class SignedUrl:
    """
    Represents a signed URL with expiration and validation.
    """

    url: str
    token: str
    expires_at: datetime
    signature: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if the signed URL has expired."""
        return datetime.utcnow() >= self.expires_at

    def get_remaining_seconds(self) -> int:
        """Get remaining seconds until expiration."""
        remaining = self.expires_at - datetime.utcnow()
        return max(0, int(remaining.total_seconds()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "url": self.url,
            "token": self.token,
            "expires_at": self.expires_at.isoformat(),
            "expires_in": self.get_remaining_seconds(),
            "signature": self.signature,
        }


class SignedUrlService:
    """
    Service for generating and validating signed URLs.

    Provides secure, time-limited access to downloaded files using
    cryptographically secure tokens and optional HMAC signatures.
    """

    def __init__(
        self, secret_key: Optional[str] = None, base_url: Optional[str] = None
    ):
        """
        Initialize SignedUrlService.

        Args:
            secret_key: Secret key for HMAC signing (optional, uses SECRET_KEY env var or generates if not provided)
            base_url: Base URL for download endpoints. If not provided, will use
                the `DOWNLOAD_BASE_URL` environment variable for public client access,
                falling back to `API_BASE_URL` for internal use. If neither is set,
                a relative path '/api/v1/downloads/file' will be used.
        """
        self.secret_key = (
            secret_key or os.getenv("SECRET_KEY") or self._generate_secret_key()
        )
        # Determine base URL priority: explicit arg > DOWNLOAD_BASE_URL env var > API_BASE_URL env var > default relative path
        if base_url:
            self.base_url = base_url
        else:
            # For downloads, use the public-facing URL if available
            download_base = os.getenv("DOWNLOAD_BASE_URL")
            if download_base:
                self.base_url = download_base.rstrip("/") + "/api/v1/downloads/file"
            else:
                # Fallback to API_BASE_URL for internal use
                api_base = os.getenv("API_BASE_URL")
                if api_base:
                    # Ensure no trailing slash
                    self.base_url = api_base.rstrip("/") + "/api/v1/downloads/file"
                else:
                    self.base_url = "/api/v1/downloads/file"

    @staticmethod
    def _generate_secret_key(length: int = 32) -> str:
        """Generate a cryptographically secure secret key."""
        return secrets.token_hex(length)

    def generate_signed_url(
        self,
        token: str,
        ttl_minutes: int = 10,
        include_signature: bool = True,
        expires_at: Optional[datetime] = None,
    ) -> SignedUrl:
        """
        Generate a signed URL for file access.

        Args:
            token: File access token
            ttl_minutes: Time to live in minutes
            include_signature: Whether to include HMAC signature for additional security
            expires_at: Optional specific expiration datetime (if not provided, calculated from ttl_minutes)

        Returns:
            SignedUrl object with URL and expiration information
        """
        if expires_at is None:
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)

        # Construct base URL
        url = f"{self.base_url}/{token}"

        # Generate HMAC signature if requested
        signature = None
        if include_signature:
            signature = self._generate_signature(token, expires_at)
            url = f"{url}?signature={signature}"

        return SignedUrl(
            url=url, token=token, expires_at=expires_at, signature=signature
        )

    def _generate_signature(self, token: str, expires_at: datetime) -> str:
        """
        Generate HMAC signature for token and expiration.

        Args:
            token: File access token
            expires_at: Expiration datetime

        Returns:
            HMAC signature as hex string
        """
        # Create message from token and expiration timestamp
        message = f"{token}:{expires_at.isoformat()}"

        # Generate HMAC-SHA256 signature
        signature = hmac.new(
            self.secret_key.encode("utf-8"), message.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        return signature

    def validate_signature(
        self, token: str, signature: str, expires_at: datetime
    ) -> bool:
        """
        Validate HMAC signature for a token.

        Args:
            token: File access token
            signature: HMAC signature to validate
            expires_at: Expiration datetime

        Returns:
            True if signature is valid, False otherwise
        """
        expected_signature = self._generate_signature(token, expires_at)

        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(signature, expected_signature)

    def validate_token(
        self,
        token: str,
        signature: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> bool:
        """
        Validate a token and optional signature.

        Args:
            token: File access token
            signature: Optional HMAC signature
            expires_at: Optional expiration datetime

        Returns:
            True if token is valid, False otherwise
        """
        # Basic token format validation
        if not token or len(token) < 16:
            return False

        # If signature provided, validate it
        if signature and expires_at:
            if not self.validate_signature(token, signature, expires_at):
                return False

        # Check expiration if provided
        if expires_at and datetime.utcnow() >= expires_at:
            return False

        return True

    def generate_download_url(self, token: str, ttl_minutes: int = 10) -> str:
        """
        Generate a simple download URL (convenience method).

        Args:
            token: File access token
            ttl_minutes: Time to live in minutes

        Returns:
            Download URL string
        """
        signed_url = self.generate_signed_url(
            token, ttl_minutes, include_signature=False
        )
        return signed_url.url
