import pytest
from src.domain.video_processing.entities import VideoFormat, VideoMetadata
from src.domain.video_processing.value_objects import FormatType


class TestVideoMetadata:
    def test_duration_formatting_hours_and_minutes(self):
        md1 = VideoMetadata(
            id="id1", title="t", uploader="u", duration=90, thumbnail="th", url="u"
        )
        assert md1.get_duration_formatted() == "01:30"
        md2 = VideoMetadata(
            id="id2", title="t2", uploader="u2", duration=3700, thumbnail="th", url="u"
        )
        assert md2.get_duration_formatted().startswith("01:")

    def test_validation_errors(self):
        with pytest.raises(ValueError):
            VideoMetadata(
                id="", title="t", uploader="u", duration=10, thumbnail="th", url="u"
            )
        with pytest.raises(ValueError):
            VideoMetadata(
                id="x", title="", uploader="u", duration=10, thumbnail="th", url="u"
            )
        with pytest.raises(ValueError):
            VideoMetadata(
                id="x", title="t", uploader="u", duration=-1, thumbnail="th", url="u"
            )


class TestVideoFormat:
    def test_type_detection_and_helpers(self):
        va = VideoFormat(
            format_id="f1",
            extension="mp4",
            resolution="1920x1080",
            height=1080,
            video_codec="h264",
            audio_codec="aac",
        )
        assert va.has_both_codecs()
        assert va.format_type == FormatType.VIDEO_AUDIO

        vo = VideoFormat(
            format_id="f2",
            extension="webm",
            resolution="1280x720",
            height=720,
            video_codec="vp9",
            audio_codec="none",
        )
        assert vo.is_video_only()
        assert vo.format_type == FormatType.VIDEO_ONLY

        ao = VideoFormat(
            format_id="f3",
            extension="m4a",
            resolution="audio",
            height=0,
            video_codec="none",
            audio_codec="aac",
        )
        assert ao.is_audio_only()
        assert ao.format_type == FormatType.AUDIO_ONLY

    def test_quality_label_and_filesize(self):
        vf = VideoFormat(
            format_id="f4",
            extension="mp4",
            resolution="3840x2160",
            height=2160,
            filesize=2 * 1024 * 1024,
        )
        assert vf.calculate_quality_label() == "Ultra"
        assert vf.get_filesize_mb() == 2.0
        assert vf.get_filesize_formatted().endswith("MB")

        big = VideoFormat(
            format_id="f5",
            extension="mp4",
            resolution="7680x4320",
            height=4320,
            filesize=2 * 1024 * 1024 * 1024,
        )
        assert big.get_filesize_formatted().endswith("GB")

    def test_validation_required_fields(self):
        with pytest.raises(ValueError):
            VideoFormat(format_id="", extension="mp4", resolution="x", height=1)
        with pytest.raises(ValueError):
            VideoFormat(format_id="f", extension="", resolution="x", height=1)
