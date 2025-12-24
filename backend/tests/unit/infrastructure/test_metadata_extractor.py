
import pytest
from unittest.mock import patch, MagicMock
from yt_dlp.utils import DownloadError

from src.infrastructure.video_metadata_extractor import VideoMetadataExtractor
from src.domain.video_processing.value_objects import YouTubeUrl
from src.domain.errors import MetadataExtractionError

@pytest.mark.unit
class TestMetadataExtractor:
    """Unit tests for VideoMetadataExtractor using mocks."""

    @pytest.fixture
    def extractor(self):
        return VideoMetadataExtractor()

    @patch("src.infrastructure.video_metadata_extractor.YoutubeDL")
    def test_extract_metadata_success(self, mock_ytdl_cls, extractor):
        """Verify successful metadata extraction."""
        # Arrange
        mock_ytdl = mock_ytdl_cls.return_value.__enter__.return_value
        mock_ytdl.extract_info.return_value = {
            "id": "vid123",
            "title": "Test Video",
            "uploader": "Tester",
            "duration": 120,
            "thumbnail": "thumb.jpg"
        }
        url = YouTubeUrl("https://youtube.com/watch?v=vid123")

        # Act
        metadata = extractor.extract_metadata(url)

        # Assert
        assert metadata.id == "vid123"
        assert metadata.title == "Test Video"
        assert metadata.duration == 120

    @patch("src.infrastructure.video_metadata_extractor.YoutubeDL")
    def test_extract_formats_parsing(self, mock_ytdl_cls, extractor):
        """Verify format parsing logic."""
        # Arrange
        mock_ytdl = mock_ytdl_cls.return_value.__enter__.return_value
        mock_ytdl.extract_info.return_value = {
            "formats": [
                {
                    "format_id": "137",
                    "ext": "mp4",
                    "height": 1080,
                    "width": 1920,
                    "filesize": 1000000,
                    "vcodec": "avc1"
                },
                {
                    "format_id": "140",
                    "ext": "m4a",
                    "height": 0,
                    "width": 0,
                    "vcodec": "none",
                    "filesize": 50000
                }
            ]
        }
        url = YouTubeUrl("https://youtube.com/watch?v=vid123")

        # Act
        formats = extractor.extract_formats(url)

        # Assert
        assert len(formats) == 2
        # First format (1080p)
        assert formats[0].format_id == "137"
        assert formats[0].resolution == "1920x1080"

        # Second format (Audio)
        assert formats[1].format_id == "140"
        assert formats[1].resolution == "audio only"

    @patch("src.infrastructure.video_metadata_extractor.YoutubeDL")
    def test_extract_filesize_fallback(self, mock_ytdl_cls, extractor):
        """Verify fallback logic for calculating filesize."""
        # Arrange
        mock_ytdl = mock_ytdl_cls.return_value.__enter__.return_value
        mock_ytdl.extract_info.return_value = {
            "formats": [
                {
                    "format_id": "approx",
                    "filesize": None,
                    "filesize_approx": 2000,
                    "height": 720
                },
                {
                    "format_id": "calc",
                    "filesize": None,
                    "filesize_approx": None,
                    "tbr": 1000, # 1000 kbps
                    "duration": 10, # 10 seconds
                    "height": 480
                }
            ]
        }
        url = YouTubeUrl("https://youtube.com/watch?v=vid123")

        # Act
        formats = extractor.extract_formats(url)

        # Find formats
        fmt_approx = next(f for f in formats if f.format_id == "approx")
        fmt_calc = next(f for f in formats if f.format_id == "calc")

        # Assert
        assert fmt_approx.filesize == 2000
        # Calculation: (1000 kbps * 10s * 1024) / 8 = 1280000 bytes
        assert fmt_calc.filesize == 1280000

    @patch("src.infrastructure.video_metadata_extractor.YoutubeDL")
    def test_extraction_error_handling(self, mock_ytdl_cls, extractor):
        """Verify errors are wrapped in MetadataExtractionError."""
        # Arrange
        mock_ytdl = mock_ytdl_cls.return_value.__enter__.return_value
        mock_ytdl.extract_info.side_effect = DownloadError("Video unavailable")
        url = YouTubeUrl("https://youtube.com/watch?v=broken")

        # Act & Assert
        with pytest.raises(MetadataExtractionError) as exc:
            extractor.extract_metadata(url)

        assert "Failed to extract metadata" in str(exc.value)
