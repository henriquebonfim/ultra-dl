"""
Unit tests for video processing value objects.

Tests verify YouTubeUrl and FormatId value object behavior including:
- Validation rules reject invalid inputs
- Immutability (cannot modify after creation)
- Equality and string representation

Requirements: 1.2, 1.4
"""

import pytest
from src.domain.video_processing.value_objects import (
    YouTubeUrl,
    FormatId,
    InvalidFormatIdError,
    FormatType
)
from src.domain.errors import InvalidUrlError


class TestYouTubeUrl:
    """Test YouTubeUrl value object."""

    def test_immutability_cannot_modify_value(self):
        """
        Test that YouTubeUrl is immutable - cannot modify value.

        Verifies that attempting to modify attributes raises AttributeError.
        """
        url = YouTubeUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        with pytest.raises(AttributeError):
            url.value = "https://www.youtube.com/watch?v=different"

    def test_validation_accepts_standard_youtube_url(self):
        """Test that standard YouTube URLs are accepted."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert url.value == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_validation_accepts_shorts_youtube_url(self):
        """Test that YouTube Shorts URLs are accepted."""
        url = YouTubeUrl("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        assert url.value == "https://www.youtube.com/shorts/dQw4w9WgXcQ"

    def test_validation_accepts_short_youtube_url(self):
        """Test that short youtu.be URLs are accepted."""
        url = YouTubeUrl("https://youtu.be/dQw4w9WgXcQ")
        assert url.value == "https://youtu.be/dQw4w9WgXcQ"

    def test_validation_accepts_mobile_youtube_url(self):
        """Test that mobile YouTube URLs are accepted."""
        url = YouTubeUrl("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert url.value == "https://m.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_validation_accepts_url_without_https(self):
        """Test that URLs without https:// are accepted."""
        url = YouTubeUrl("http://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert url.value == "http://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_validation_rejects_non_youtube_url(self):
        """Test that non-YouTube URLs are rejected."""
        with pytest.raises(InvalidUrlError) as exc_info:
            YouTubeUrl("https://vimeo.com/123456789")
        assert "Invalid YouTube URL" in str(exc_info.value)

    def test_validation_rejects_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(InvalidUrlError):
            YouTubeUrl("")

    def test_validation_rejects_malformed_url(self):
        """Test that malformed URLs are rejected."""
        with pytest.raises(InvalidUrlError):
            YouTubeUrl("not-a-valid-url")

    def test_validation_rejects_youtube_url_without_video_id(self):
        """Test that YouTube URLs without video ID are rejected."""
        with pytest.raises(InvalidUrlError):
            YouTubeUrl("https://www.youtube.com/watch")

    def test_extract_video_id_from_standard_url(self):
        """Test extracting video ID from standard YouTube URL."""
        url = YouTubeUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        video_id = url.extract_video_id()
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_from_shorts_url(self):
        """Test extracting video ID from YouTube Shorts URL."""
        url = YouTubeUrl("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        video_id = url.extract_video_id()
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_from_short_url(self):
        """Test extracting video ID from short youtu.be URL."""
        url = YouTubeUrl("https://youtu.be/dQw4w9WgXcQ")
        video_id = url.extract_video_id()
        assert video_id == "dQw4w9WgXcQ"

    def test_string_representation(self):
        """Test that __str__ returns the URL value."""
        url_string = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        url = YouTubeUrl(url_string)
        assert str(url) == url_string

    def test_equality_same_url(self):
        """Test that URLs with same value are equal."""
        url1 = YouTubeUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        url2 = YouTubeUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert url1 == url2

    def test_equality_different_url(self):
        """Test that URLs with different values are not equal."""
        url1 = YouTubeUrl("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        url2 = YouTubeUrl("https://www.youtube.com/watch?v=different123")
        assert url1 != url2


class TestFormatId:
    """Test FormatId value object."""

    def test_immutability_cannot_modify_value(self):
        """
        Test that FormatId is immutable - cannot modify value.

        Verifies that attempting to modify attributes raises AttributeError.
        """
        format_id = FormatId("best")

        with pytest.raises(AttributeError):
            format_id.value = "worst"

    def test_validation_accepts_keyword_best(self):
        """Test that 'best' keyword is accepted."""
        format_id = FormatId("best")
        assert format_id.value == "best"

    def test_validation_accepts_keyword_worst(self):
        """Test that 'worst' keyword is accepted."""
        format_id = FormatId("worst")
        assert format_id.value == "worst"

    def test_validation_accepts_keyword_bestaudio(self):
        """Test that 'bestaudio' keyword is accepted."""
        format_id = FormatId("bestaudio")
        assert format_id.value == "bestaudio"

    def test_validation_accepts_keyword_bestvideo(self):
        """Test that 'bestvideo' keyword is accepted."""
        format_id = FormatId("bestvideo")
        assert format_id.value == "bestvideo"

    def test_validation_accepts_keyword_worstaudio(self):
        """Test that 'worstaudio' keyword is accepted."""
        format_id = FormatId("worstaudio")
        assert format_id.value == "worstaudio"

    def test_validation_accepts_keyword_worstvideo(self):
        """Test that 'worstvideo' keyword is accepted."""
        format_id = FormatId("worstvideo")
        assert format_id.value == "worstvideo"

    def test_validation_accepts_numeric_format(self):
        """Test that numeric format IDs are accepted."""
        format_id = FormatId("137")
        assert format_id.value == "137"

    def test_validation_accepts_combined_numeric_format(self):
        """Test that combined numeric formats are accepted."""
        format_id = FormatId("137+140")
        assert format_id.value == "137+140"

    def test_validation_accepts_combined_keyword_format(self):
        """Test that combined keyword formats are accepted."""
        format_id = FormatId("bestvideo+bestaudio")
        assert format_id.value == "bestvideo+bestaudio"

    def test_validation_accepts_mixed_combined_format(self):
        """Test that mixed combined formats are accepted."""
        format_id = FormatId("137+bestaudio")
        assert format_id.value == "137+bestaudio"

    def test_validation_rejects_empty_string(self):
        """Test that empty string is rejected."""
        with pytest.raises(InvalidFormatIdError) as exc_info:
            FormatId("")
        assert "Invalid format ID" in str(exc_info.value)

    def test_validation_rejects_invalid_keyword(self):
        """Test that invalid keywords are rejected."""
        with pytest.raises(InvalidFormatIdError):
            FormatId("excellent")

    def test_validation_rejects_special_characters(self):
        """Test that format IDs with special characters are rejected."""
        with pytest.raises(InvalidFormatIdError):
            FormatId("best@video")

    def test_validation_rejects_spaces(self):
        """Test that format IDs with spaces are rejected."""
        with pytest.raises(InvalidFormatIdError):
            FormatId("best video")

    def test_is_combined_returns_true_for_combined_format(self):
        """Test that is_combined() returns True for combined formats."""
        format_id = FormatId("137+140")
        assert format_id.is_combined() is True

    def test_is_combined_returns_false_for_single_format(self):
        """Test that is_combined() returns False for single formats."""
        format_id = FormatId("best")
        assert format_id.is_combined() is False

    def test_string_representation(self):
        """Test that __str__ returns the format ID value."""
        format_id = FormatId("best")
        assert str(format_id) == "best"

    def test_equality_same_format(self):
        """Test that format IDs with same value are equal."""
        format1 = FormatId("best")
        format2 = FormatId("best")
        assert format1 == format2

    def test_equality_different_format(self):
        """Test that format IDs with different values are not equal."""
        format1 = FormatId("best")
        format2 = FormatId("worst")
        assert format1 != format2


class TestFormatType:
    """Test FormatType enumeration."""

    def test_all_format_types_exist(self):
        """Test that all expected format types are defined."""
        assert FormatType.VIDEO_AUDIO.value == "video+audio"
        assert FormatType.VIDEO_ONLY.value == "video_only"
        assert FormatType.AUDIO_ONLY.value == "audio_only"

    def test_equality(self):
        """Test that format types can be compared for equality."""
        type1 = FormatType.VIDEO_AUDIO
        type2 = FormatType.VIDEO_AUDIO
        type3 = FormatType.AUDIO_ONLY

        assert type1 == type2
        assert type1 != type3

    def test_string_representation(self):
        """Test that format types have correct string representation."""
        assert str(FormatType.VIDEO_AUDIO.value) == "video+audio"
        assert str(FormatType.VIDEO_ONLY.value) == "video_only"
        assert str(FormatType.AUDIO_ONLY.value) == "audio_only"
