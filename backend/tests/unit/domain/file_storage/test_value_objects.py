"""
Unit tests for file storage value objects.

Tests verify DownloadToken value object behavior including:
- Validation rules reject invalid inputs
- Immutability (cannot modify after creation)
- Equality and string representation
- Token generation

Requirements: 1.2, 1.4
"""

import pytest
from src.domain.file_storage.value_objects import DownloadToken, InvalidDownloadTokenError


class TestDownloadToken:
    """Test DownloadToken value object."""
    
    def test_immutability_cannot_modify_value(self):
        """
        Test that DownloadToken is immutable - cannot modify value.
        
        Verifies that attempting to modify attributes raises AttributeError.
        """
        token = DownloadToken.generate()
        
        with pytest.raises(AttributeError):
            token.value = "different_token_value_that_is_long_enough"
    
    def test_validation_accepts_valid_token_32_chars(self):
        """Test that tokens with exactly 32 characters are accepted."""
        token_value = "a" * 32
        token = DownloadToken(token_value)
        assert token.value == token_value
    
    def test_validation_accepts_valid_token_longer_than_32(self):
        """Test that tokens longer than 32 characters are accepted."""
        token_value = "a" * 50
        token = DownloadToken(token_value)
        assert token.value == token_value
    
    def test_validation_accepts_alphanumeric_token(self):
        """Test that alphanumeric tokens are accepted."""
        token_value = "abc123XYZ789" + "a" * 20
        token = DownloadToken(token_value)
        assert token.value == token_value
    
    def test_validation_accepts_token_with_hyphens(self):
        """Test that tokens with hyphens are accepted."""
        token_value = "abc-123-xyz-789" + "a" * 17
        token = DownloadToken(token_value)
        assert token.value == token_value
    
    def test_validation_accepts_token_with_underscores(self):
        """Test that tokens with underscores are accepted."""
        token_value = "abc_123_xyz_789" + "a" * 17
        token = DownloadToken(token_value)
        assert token.value == token_value
    
    def test_validation_rejects_token_too_short(self):
        """Test that tokens shorter than 32 characters are rejected."""
        token_value = "a" * 31
        with pytest.raises(InvalidDownloadTokenError) as exc_info:
            DownloadToken(token_value)
        assert "must be at least 32 characters" in str(exc_info.value)
        assert "got 31" in str(exc_info.value)
    
    def test_validation_rejects_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(InvalidDownloadTokenError):
            DownloadToken("")
    
    def test_validation_rejects_token_with_special_characters(self):
        """Test that tokens with special characters are rejected."""
        token_value = "abc@123#xyz$789" + "a" * 17
        with pytest.raises(InvalidDownloadTokenError):
            DownloadToken(token_value)
    
    def test_validation_rejects_token_with_spaces(self):
        """Test that tokens with spaces are rejected."""
        token_value = "abc 123 xyz 789" + "a" * 17
        with pytest.raises(InvalidDownloadTokenError):
            DownloadToken(token_value)
    
    def test_generate_creates_valid_token(self):
        """Test that generate() creates a valid token."""
        token = DownloadToken.generate()
        
        # Token should be valid (no exception raised)
        assert token is not None
        assert len(token.value) >= 32
        # Token should be URL-safe
        assert all(c.isalnum() or c in "-_" for c in token.value)
    
    def test_generate_creates_unique_tokens(self):
        """Test that generate() creates unique tokens."""
        tokens = [DownloadToken.generate() for _ in range(100)]
        token_values = [str(token) for token in tokens]
        
        # All tokens should be unique
        assert len(token_values) == len(set(token_values))
    
    def test_generate_creates_tokens_with_sufficient_length(self):
        """Test that generated tokens are sufficiently long."""
        token = DownloadToken.generate()
        
        # secrets.token_urlsafe(32) generates approximately 43 characters
        assert len(token.value) >= 32
        assert len(token.value) <= 50  # Reasonable upper bound
    
    def test_string_representation(self):
        """Test that __str__ returns the token value."""
        token_value = "test_token_" + "a" * 22
        token = DownloadToken(token_value)
        assert str(token) == token_value
    
    def test_equality_same_token(self):
        """Test that tokens with same value are equal."""
        token_value = "test_token_" + "a" * 22
        token1 = DownloadToken(token_value)
        token2 = DownloadToken(token_value)
        assert token1 == token2
    
    def test_equality_different_token(self):
        """Test that tokens with different values are not equal."""
        token1 = DownloadToken("test_token_1_" + "a" * 19)
        token2 = DownloadToken("test_token_2_" + "b" * 19)
        assert token1 != token2
    
    def test_token_can_be_used_as_dict_key(self):
        """Test that tokens can be used as dictionary keys (hashable)."""
        token1 = DownloadToken.generate()
        token2 = DownloadToken.generate()
        
        token_dict = {
            token1: "value1",
            token2: "value2"
        }
        
        assert token_dict[token1] == "value1"
        assert token_dict[token2] == "value2"
    
    def test_token_can_be_used_in_set(self):
        """Test that tokens can be used in sets (hashable)."""
        token1 = DownloadToken.generate()
        token2 = DownloadToken.generate()
        token3 = DownloadToken(str(token1))  # Same value as token1
        
        token_set = {token1, token2, token3}
        
        # token1 and token3 have same value, so set should have 2 elements
        assert len(token_set) == 2
