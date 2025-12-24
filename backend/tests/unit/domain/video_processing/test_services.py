import pytest
from src.domain.video_processing.entities import VideoFormat, VideoMetadata
from src.domain.video_processing.repositories import IVideoMetadataExtractor
from src.domain.video_processing.services import VideoProcessor
from src.domain.video_processing.value_objects import FormatType, InvalidUrlError


class StubExtractor(IVideoMetadataExtractor):
    def __init__(self):
        self.last_url = None

    def extract_metadata(self, url):
        self.last_url = str(url)
        return VideoMetadata(
            id="vid123",
            title="Sample",
            uploader="uploader",
            duration=120,
            thumbnail="http://thumb",
            url=str(url),
        )

    def extract_formats(self, url):
        self.last_url = str(url)
        return [
            VideoFormat(
                format_id="va1",
                extension="mp4",
                resolution="1920x1080",
                height=1080,
                video_codec="h264",
                audio_codec="aac",
                quality_label="1080p",
            ),
            VideoFormat(
                format_id="vo1",
                extension="webm",
                resolution="1280x720",
                height=720,
                video_codec="vp9",
                audio_codec="none",
                quality_label="720p",
            ),
            VideoFormat(
                format_id="ao1",
                extension="m4a",
                resolution="audio",
                height=0,
                video_codec="none",
                audio_codec="aac",
                quality_label="audio",
            ),
        ]


class TestVideoProcessorValidation:
    def test_validate_url_true_for_valid(self):
        vp = VideoProcessor(StubExtractor())
        assert vp.validate_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True

    def test_validate_url_false_for_invalid(self):
        vp = VideoProcessor(StubExtractor())
        assert vp.validate_url("not-a-url") is False


class TestVideoProcessorExtraction:
    def test_extract_metadata_validates_and_delegates(self):
        ex = StubExtractor()
        vp = VideoProcessor(ex)
        md = vp.extract_metadata("https://youtu.be/dQw4w9WgXcQ")
        assert md.id == "vid123"
        assert ex.last_url.endswith("dQw4w9WgXcQ")

    def test_extract_metadata_invalid_url_raises(self):
        vp = VideoProcessor(StubExtractor())
        with pytest.raises(InvalidUrlError):
            vp.extract_metadata("invalid")

    def test_get_available_formats_validates_and_delegates(self):
        ex = StubExtractor()
        vp = VideoProcessor(ex)
        formats = vp.get_available_formats(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        )
        assert len(formats) == 3
        assert any(f.has_both_codecs() for f in formats)


class TestFormatsToFrontendList:
    def test_grouping_and_sorting_by_type_and_height(self):
        ex = StubExtractor()
        vp = VideoProcessor(ex)
        formats = ex.extract_formats("https://www.youtube.com/watch?v=dQw4w9WgXcQ")

        result = vp.formats_to_frontend_list(formats)

        # Expect order: video+audio (height desc), then video_only, then audio_only
        types = [item["type"] for item in result]
        heights = [item["height"] for item in result]

        # First should be video+audio, then video_only, and last audio_only
        assert types[0] == FormatType.VIDEO_AUDIO.value
        assert FormatType.VIDEO_ONLY.value in types
        assert FormatType.AUDIO_ONLY.value in types

        # Video+Audio listed before video_only and audio_only
        first_va_index = types.index(FormatType.VIDEO_AUDIO.value)
        first_vo_index = types.index(FormatType.VIDEO_ONLY.value)
        first_ao_index = types.index(FormatType.AUDIO_ONLY.value)
        assert first_va_index < first_vo_index < first_ao_index

        # Fields exist and note is default string
        first = result[0]
        assert {
            "format_id",
            "ext",
            "resolution",
            "height",
            "note",
            "filesize",
            "vcodec",
            "acodec",
            "quality_label",
            "type",
        }.issubset(first.keys())
        assert isinstance(first["note"], str)
