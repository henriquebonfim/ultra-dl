"""
File Storage Value Objects

Immutable value objects for type safety and validation.
"""

from dataclasses import dataclass
import secrets


class InvalidDownloadTokenError(ValueError):
    """Raised when a download token is invalid."""
    pass


@dataclass(frozen=True)
class DownloadToken:
    """
    Value object representing a validated download token.
    
    Ensures tokens are cryptographically secure and meet minimum length requirements.
    Tokens must be at least 32 characters long and URL-safe.
    """
    value: str
    
    def __post_init__(self):
        if not self._is_valid():
            raise InvalidDownloadTokenError(
                f"Invalid download token: must be at least 32 characters, got {len(self.value)}"
            )
    
    def _is_valid(self) -> bool:
        """
        Validate download token.
        
        Requirements:
        - Must be a string
        - Must be at least 32 characters long
        - Should be URL-safe (alphanumeric, hyphens, underscores)
        """
        if not self.value or not isinstance(self.value, str):
            return False
        
        if len(self.value) < 32:
            return False
        
        # Check if URL-safe (alphanumeric + - and _)
        return all(c.isalnum() or c in '-_' for c in self.value)
    
    @classmethod
    def generate(cls) -> 'DownloadToken':
        """
        Generate a new cryptographically secure download token.
        
        Uses secrets.token_urlsafe(32) to generate a URL-safe token
        with 32 bytes of randomness (approximately 43 characters when base64 encoded).
        
        Returns:
            New DownloadToken instance with generated value
        """
        token_value = secrets.token_urlsafe(32)
        return cls(token_value)
    
    def __str__(self) -> str:
        return self.value
