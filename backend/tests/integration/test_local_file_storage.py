
import pytest
import os
from pathlib import Path
from io import BytesIO

from src.infrastructure.local_file_storage_repository import LocalFileStorageRepository

@pytest.mark.integration
class TestLocalFileStorageIntegration:
    """Integration tests for LocalFileStorageRepository using real filesystem."""

    @pytest.fixture
    def storage_repo(self, tmp_path):
        """Create a repository instance using a pytest-managed temporary directory."""
        return LocalFileStorageRepository(base_path=str(tmp_path))

    def test_save_and_get_file(self, storage_repo):
        """Verify file can be saved to disk and retrieved."""
        # Arrange
        file_path = "test_folder/test_file.txt"
        content_data = b"Hello, Integration World!"
        content_stream = BytesIO(content_data)

        # Act
        save_result = storage_repo.save(file_path, content_stream)

        # Assert - Save
        assert save_result is True
        assert storage_repo.exists(file_path) is True

        # Act - Retrieve
        retrieved_content = storage_repo.get(file_path)

        # Assert - Retrieve
        assert retrieved_content is not None
        assert retrieved_content.read() == content_data

    def test_delete_file(self, storage_repo):
        """Verify file deletion works on disk."""
        # Arrange
        file_path = "todelete.txt"
        storage_repo.save(file_path, BytesIO(b"delete me"))
        assert storage_repo.exists(file_path) is True

        # Act
        delete_result = storage_repo.delete(file_path)

        # Assert
        assert delete_result is True
        assert storage_repo.exists(file_path) is False

    def test_ensure_directory_creation(self, storage_repo, tmp_path):
        """Verify that nested directories are automatically created."""
        # Arrange
        deep_path = "level1/level2/level3/deep.txt"

        # Act
        storage_repo.save(deep_path, BytesIO(b"deep content"))

        # Assert
        full_path = tmp_path / "level1" / "level2" / "level3" / "deep.txt"
        assert full_path.exists()
        assert full_path.is_file()

    def test_get_nonexistent_file(self, storage_repo):
        """Verify behavior when requesting a file that doesn't exist."""
        result = storage_repo.get("ghost_file.txt")
        assert result is None

    def test_get_size(self, storage_repo):
        """Verify file size retrieval."""
        # Arrange
        file_path = "size.txt"
        data = b"12345" # 5 bytes
        storage_repo.save(file_path, BytesIO(data))

        # Act
        size = storage_repo.get_size(file_path)

        # Assert
        assert size == 5
