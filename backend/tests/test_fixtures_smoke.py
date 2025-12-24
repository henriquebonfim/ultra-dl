"""
Smoke test for fixtures to verify they work correctly.
"""
import pytest
from tests.fixtures import (
    create_download_job,
    create_job_archive,
    create_downloaded_file,
    create_video_metadata,
    create_video_format,
    create_youtube_url,
    create_format_id,
    create_download_token,
    create_job_progress,
    MockJobRepository,
    MockFileRepository,
    MockStorageRepository,
    MockMetadataExtractor,
    MockArchiveRepository,
)


class TestDomainEntityFactories:
    """Test domain entity factory functions."""
    
    def test_create_download_job(self):
        """Test DownloadJob factory creates valid entity."""
        job = create_download_job()
        assert job.job_id is not None
        assert job.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert str(job.format_id) == "best"
    
    def test_create_job_archive(self):
        """Test JobArchive factory creates valid entity."""
        archive = create_job_archive()
        assert archive.job_id is not None
        assert archive.status == "completed"
    
    def test_create_downloaded_file(self):
        """Test DownloadedFile factory creates valid entity."""
        file = create_downloaded_file()
        assert file.job_id is not None
        assert file.filename == "test_video.mp4"
        assert file.token is not None
    
    def test_create_video_metadata(self):
        """Test VideoMetadata factory creates valid entity."""
        metadata = create_video_metadata()
        assert metadata.id == "dQw4w9WgXcQ"
        assert metadata.title == "Test Video Title"
    
    def test_create_video_format(self):
        """Test VideoFormat factory creates valid entity."""
        fmt = create_video_format()
        assert fmt.format_id == "137"
        assert fmt.height == 1080
    


class TestValueObjectFactories:
    """Test value object factory functions."""
    
    def test_create_youtube_url(self):
        """Test YouTubeUrl factory creates valid value object."""
        url = create_youtube_url()
        assert "youtube.com" in url.value
    
    def test_create_format_id(self):
        """Test FormatId factory creates valid value object."""
        format_id = create_format_id()
        assert format_id.value == "best"
    
    def test_create_download_token(self):
        """Test DownloadToken factory creates valid value object."""
        token = create_download_token()
        assert len(str(token)) >= 32
    
    def test_create_job_progress(self):
        """Test JobProgress factory creates valid value object."""
        progress = create_job_progress()
        assert progress.percentage == 0
        assert progress.phase == "initializing"
    


class TestMockRepositories:
    """Test mock repository implementations."""
    
    def test_mock_job_repository(self):
        """Test MockJobRepository basic operations."""
        repo = MockJobRepository()
        job = create_download_job()
        
        # Save and retrieve
        assert repo.save(job) is True
        retrieved = repo.get(job.job_id)
        assert retrieved is not None
        assert retrieved.job_id == job.job_id
        
        # Delete
        assert repo.delete(job.job_id) is True
        assert repo.get(job.job_id) is None
    
    def test_mock_file_repository(self):
        """Test MockFileRepository basic operations."""
        repo = MockFileRepository()
        file = create_downloaded_file()
        
        # Save and retrieve
        assert repo.save(file) is True
        retrieved = repo.get_by_token(str(file.token))
        assert retrieved is not None
        assert retrieved.job_id == file.job_id
        
        # Get by job ID
        by_job = repo.get_by_job_id(file.job_id)
        assert by_job is not None
    
    def test_mock_storage_repository(self):
        """Test MockStorageRepository basic operations."""
        repo = MockStorageRepository()
        
        # Save and check exists
        assert repo.save("test.txt", b"hello") is True
        assert repo.exists("test.txt") is True
        
        # Get size
        assert repo.get_size("test.txt") == 5
        
        # Delete
        assert repo.delete("test.txt") is True
        assert repo.exists("test.txt") is False
    
    def test_mock_metadata_extractor(self):
        """Test MockMetadataExtractor basic operations."""
        extractor = MockMetadataExtractor()
        
        metadata = extractor.extract_metadata("https://youtube.com/watch?v=test")
        assert "title" in metadata
        
        formats = extractor.extract_formats("https://youtube.com/watch?v=test")
        assert len(formats) > 0
    
    def test_mock_archive_repository(self):
        """Test MockArchiveRepository basic operations."""
        repo = MockArchiveRepository()
        archive = create_job_archive()
        
        # Save and retrieve
        assert repo.save(archive) is True
        retrieved = repo.get(archive.job_id)
        assert retrieved is not None
