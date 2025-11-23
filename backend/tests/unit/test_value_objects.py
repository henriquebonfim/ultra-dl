"""
Unit tests for domain value objects.

Tests FormatId and other value objects for validation and behavior.
"""

try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

from domain.video_processing.value_objects import FormatId, InvalidFormatIdError
from domain.file_storage.value_objects import DownloadToken, InvalidDownloadTokenError


def test_valid_numeric_format_ids():
    """Test valid numeric format IDs."""
    print("\n=== Testing Valid Numeric Format IDs ===")
    
    # Single numeric formats
    valid_numeric = ["137", "140", "251", "22", "18"]
    
    for format_str in valid_numeric:
        format_id = FormatId(format_str)
        assert format_id.value == format_str
        assert not format_id.is_combined()
        print(f"✓ Valid numeric format: {format_str}")
    
    print("✓ All numeric format IDs validated successfully")


def test_valid_combined_format_ids():
    """Test valid combined format IDs."""
    print("\n=== Testing Valid Combined Format IDs ===")
    
    # Combined numeric formats
    combined_formats = [
        "137+140",
        "137+140+251",
        "bestvideo+bestaudio",
        "137+bestaudio",
        "bestvideo+140"
    ]
    
    for format_str in combined_formats:
        format_id = FormatId(format_str)
        assert format_id.value == format_str
        assert format_id.is_combined()
        print(f"✓ Valid combined format: {format_str}")
    
    print("✓ All combined format IDs validated successfully")


def test_valid_keyword_format_ids():
    """Test valid keyword format IDs."""
    print("\n=== Testing Valid Keyword Format IDs ===")
    
    # Keyword formats
    keywords = [
        "best",
        "worst",
        "bestaudio",
        "bestvideo",
        "worstaudio",
        "worstvideo"
    ]
    
    for format_str in keywords:
        format_id = FormatId(format_str)
        assert format_id.value == format_str
        assert not format_id.is_combined()
        print(f"✓ Valid keyword format: {format_str}")
    
    print("✓ All keyword format IDs validated successfully")


def test_invalid_format_ids_raise_value_error():
    """Test invalid format IDs raise ValueError."""
    print("\n=== Testing Invalid Format IDs ===")
    
    # Invalid formats
    invalid_formats = [
        ("", InvalidFormatIdError),                    # Empty string
        ("   ", InvalidFormatIdError),                 # Whitespace only
        ("invalid!", InvalidFormatIdError),            # Special characters
        ("137+", InvalidFormatIdError),                # Trailing plus
        ("+140", InvalidFormatIdError),                # Leading plus
        ("137++140", InvalidFormatIdError),            # Double plus
        ("abc", InvalidFormatIdError),                 # Invalid keyword
        ("137+abc", InvalidFormatIdError),             # Invalid combined
        ("best+worst+invalid", InvalidFormatIdError),  # Invalid in combination
    ]
    
    for format_str, expected_error in invalid_formats:
        if HAS_PYTEST:
            with pytest.raises(expected_error):
                format_id = FormatId(format_str)
            print(f"✓ Correctly rejected invalid format: {format_str}")
        else:
            # Manual testing without pytest
            try:
                format_id = FormatId(format_str)
                print(f"✗ Should have raised error for: {format_str}")
                raise AssertionError(f"Expected {expected_error.__name__} for {format_str}")
            except expected_error:
                print(f"✓ Correctly rejected invalid format: {format_str}")
    
    print("✓ All invalid format IDs correctly rejected")


def test_is_combined_method():
    """Test is_combined() method."""
    print("\n=== Testing is_combined() Method ===")
    
    # Test combined formats
    combined = ["137+140", "bestvideo+bestaudio", "137+140+251"]
    for format_str in combined:
        format_id = FormatId(format_str)
        assert format_id.is_combined() is True
        print(f"✓ {format_str} correctly identified as combined")
    
    # Test non-combined formats
    non_combined = ["137", "best", "bestaudio", "140"]
    for format_str in non_combined:
        format_id = FormatId(format_str)
        assert format_id.is_combined() is False
        print(f"✓ {format_str} correctly identified as non-combined")
    
    print("✓ is_combined() method works correctly")


def test_format_id_immutability():
    """Test that FormatId is immutable (frozen dataclass)."""
    print("\n=== Testing FormatId Immutability ===")
    
    format_id = FormatId("137+140")
    
    # Attempt to modify value should raise error
    if HAS_PYTEST:
        with pytest.raises(AttributeError):
            format_id.value = "999"
    else:
        try:
            format_id.value = "999"
            print("✗ Should have raised AttributeError")
            raise AssertionError("Expected AttributeError for immutability")
        except AttributeError:
            pass
    
    print("✓ FormatId is immutable")


def test_format_id_string_representation():
    """Test string representation of FormatId."""
    print("\n=== Testing FormatId String Representation ===")
    
    format_id = FormatId("137+140")
    assert str(format_id) == "137+140"
    print(f"✓ String representation: {str(format_id)}")
    
    format_id2 = FormatId("best")
    assert str(format_id2) == "best"
    print(f"✓ String representation: {str(format_id2)}")
    
    print("✓ String representation works correctly")


def test_download_token_generate_creates_valid_tokens():
    """Test that generate() creates valid tokens."""
    print("\n=== Testing DownloadToken.generate() ===")
    
    # Generate multiple tokens
    tokens = [DownloadToken.generate() for _ in range(5)]
    
    for i, token in enumerate(tokens, 1):
        # Verify token is valid
        assert isinstance(token, DownloadToken)
        assert isinstance(token.value, str)
        assert len(token.value) >= 32
        print(f"✓ Generated token {i}: {len(token.value)} characters")
    
    # Verify tokens are unique
    token_values = [t.value for t in tokens]
    assert len(set(token_values)) == len(token_values)
    print("✓ All generated tokens are unique")
    
    print("✓ DownloadToken.generate() creates valid tokens")


def test_download_token_minimum_length():
    """Test tokens are at least 32 characters."""
    print("\n=== Testing DownloadToken Minimum Length ===")
    
    # Generate token and verify length
    token = DownloadToken.generate()
    assert len(token.value) >= 32
    print(f"✓ Generated token length: {len(token.value)} (>= 32)")
    
    # Test valid 32-character token
    valid_32_char = "a" * 32
    token_32 = DownloadToken(valid_32_char)
    assert len(token_32.value) == 32
    print("✓ 32-character token accepted")
    
    # Test valid longer token
    valid_43_char = "a" * 43
    token_43 = DownloadToken(valid_43_char)
    assert len(token_43.value) == 43
    print("✓ 43-character token accepted")
    
    print("✓ Token minimum length validation works correctly")


def test_download_token_url_safe():
    """Test tokens are URL-safe."""
    print("\n=== Testing DownloadToken URL-Safety ===")
    
    # Generate multiple tokens and verify they're URL-safe
    for i in range(10):
        token = DownloadToken.generate()
        # URL-safe characters: alphanumeric, hyphen, underscore
        assert all(c.isalnum() or c in '-_' for c in token.value)
        print(f"✓ Token {i+1} is URL-safe")
    
    # Test valid URL-safe characters
    valid_tokens = [
        "a" * 32,
        "A" * 32,
        "0" * 32,
        "abc123-_" * 4,  # 32 characters
        "ABC-123_xyz" * 3 + "AB",  # 35 characters
    ]
    
    for token_str in valid_tokens:
        token = DownloadToken(token_str)
        assert token.value == token_str
        print(f"✓ Valid URL-safe token accepted: {token_str[:20]}...")
    
    print("✓ All tokens are URL-safe")


def test_download_token_invalid_raises_value_error():
    """Test invalid tokens raise ValueError."""
    print("\n=== Testing Invalid DownloadToken ===")
    
    # Invalid tokens
    invalid_tokens = [
        ("", InvalidDownloadTokenError),                    # Empty string
        ("short", InvalidDownloadTokenError),               # Too short
        ("a" * 31, InvalidDownloadTokenError),              # 31 characters (< 32)
        ("a" * 32 + "!", InvalidDownloadTokenError),        # Contains invalid character
        ("a" * 32 + " ", InvalidDownloadTokenError),        # Contains space
        ("a" * 32 + "@", InvalidDownloadTokenError),        # Contains special char
        ("hello world" * 3, InvalidDownloadTokenError),     # Contains spaces
    ]
    
    for token_str, expected_error in invalid_tokens:
        if HAS_PYTEST:
            with pytest.raises(expected_error):
                token = DownloadToken(token_str)
            print(f"✓ Correctly rejected invalid token: {repr(token_str[:20])}")
        else:
            # Manual testing without pytest
            try:
                token = DownloadToken(token_str)
                print(f"✗ Should have raised error for: {repr(token_str[:20])}")
                raise AssertionError(f"Expected {expected_error.__name__} for {repr(token_str[:20])}")
            except expected_error:
                print(f"✓ Correctly rejected invalid token: {repr(token_str[:20])}")
    
    print("✓ All invalid tokens correctly rejected")


def test_download_token_immutability():
    """Test that DownloadToken is immutable (frozen dataclass)."""
    print("\n=== Testing DownloadToken Immutability ===")
    
    token = DownloadToken.generate()
    
    # Attempt to modify value should raise error
    if HAS_PYTEST:
        with pytest.raises(AttributeError):
            token.value = "modified"
    else:
        try:
            token.value = "modified"
            print("✗ Should have raised AttributeError")
            raise AssertionError("Expected AttributeError for immutability")
        except AttributeError:
            pass
    
    print("✓ DownloadToken is immutable")


def test_download_token_string_representation():
    """Test string representation of DownloadToken."""
    print("\n=== Testing DownloadToken String Representation ===")
    
    token = DownloadToken.generate()
    assert str(token) == token.value
    print(f"✓ String representation: {str(token)[:20]}...")
    
    custom_token = DownloadToken("a" * 32)
    assert str(custom_token) == "a" * 32
    print(f"✓ String representation: {str(custom_token)[:20]}...")
    
    print("✓ String representation works correctly")


if __name__ == "__main__":
    """Run tests manually for debugging."""
    print("=" * 60)
    print("Running Value Object Tests")
    print("=" * 60)
    
    try:
        # FormatId tests
        print("\n" + "=" * 60)
        print("FormatId Tests")
        print("=" * 60)
        test_valid_numeric_format_ids()
        test_valid_combined_format_ids()
        test_valid_keyword_format_ids()
        test_invalid_format_ids_raise_value_error()
        test_is_combined_method()
        test_format_id_immutability()
        test_format_id_string_representation()
        
        # DownloadToken tests
        print("\n" + "=" * 60)
        print("DownloadToken Tests")
        print("=" * 60)
        test_download_token_generate_creates_valid_tokens()
        test_download_token_minimum_length()
        test_download_token_url_safe()
        test_download_token_invalid_raises_value_error()
        test_download_token_immutability()
        test_download_token_string_representation()
        
        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"✗ TEST FAILED: {e}")
        print("=" * 60)
        raise
