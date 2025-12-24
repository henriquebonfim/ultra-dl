import io
import os
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from src.domain.file_storage.entities import DownloadedFile
from src.domain.file_storage.repositories import FileRepository
from src.domain.file_storage.services import (
    FileExpiredError,
    FileManager,
    FileNotFoundError,
)
from src.domain.file_storage.storage_repository import IFileStorageRepository


class InMemoryFileRepo(FileRepository):
    def __init__(self):
        self.by_token = {}
        self.by_job = {}

    def save(self, file: DownloadedFile) -> bool:
        self.by_token[str(file.token)] = file
        self.by_job[file.job_id] = file
        return True

    def get_by_token(self, token: str):
        key = str(token)
        return self.by_token.get(key)

    def get_by_job_id(self, job_id: str):
        return self.by_job.get(job_id)

    def delete(self, token: str) -> bool:
        key = str(token)
        f = self.by_token.pop(key, None)
        if f and self.by_job.get(f.job_id) is f:
            self.by_job.pop(f.job_id, None)
        return True

    def get_expired_files(self):
        return [f for f in self.by_token.values() if f.is_expired()]

    def exists(self, token: str) -> bool:
        return str(token) in self.by_token


class DummyStorageRepo(IFileStorageRepository):
    def __init__(self):
        self.deleted = []

    def save(self, file_path: str, content: io.BufferedReader) -> bool:
        return True

    def get(self, file_path: str):
        return None

    def delete(self, file_path: str) -> bool:
        self.deleted.append(file_path)
        return True

    def exists(self, file_path: str) -> bool:
        return Path(file_path).exists()

    def get_size(self, file_path: str):
        try:
            return os.path.getsize(file_path)
        except Exception:
            return None


def create_temp_file(tmp_path, name="video.bin", size=16):
    p = tmp_path / name
    p.write_bytes(b"x" * size)
    return str(p)


class TestFileManagerRegister:
    def test_register_file_success(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        file_path = create_temp_file(tmp_path, size=32)
        result = mgr.register_file(
            file_path, job_id="job-1", filename="orig.mp4", ttl_minutes=1
        )

        assert isinstance(result, DownloadedFile)
        assert result.job_id == "job-1"
        assert result.filename == "orig.mp4"
        assert result.filesize == 32
        # saved in repo
        assert repo.exists(str(result.token))

    def test_register_file_missing_raises(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        with pytest.raises(FileNotFoundError):
            mgr.register_file(
                str(tmp_path / "missing.bin"), job_id="job-x", filename="x"
            )


class TestFileManagerRetrieval:
    def test_get_file_by_token_returns_file_when_not_expired(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="j1", filename="f1", ttl_minutes=10)
        repo.save(f)

        got = mgr.get_file_by_token(str(f.token))
        assert got is f

    def test_get_file_by_token_expired_deletes_and_raises(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="j2", filename="f2", ttl_minutes=0)
        # force expiration in the past
        f.expires_at = datetime.utcnow() - timedelta(seconds=1)
        repo.save(f)

        with pytest.raises(FileExpiredError):
            mgr.get_file_by_token(str(f.token))
        # metadata deleted and physical attempted
        assert not repo.exists(str(f.token))
        assert fp in storage.deleted

    def test_get_file_by_job_id_expired_returns_none_and_deletes(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="job-exp", filename="f3", ttl_minutes=0)
        f.expires_at = datetime.utcnow() - timedelta(seconds=1)
        repo.save(f)

        got = mgr.get_file_by_job_id("job-exp")
        assert got is None
        assert not repo.exists(str(f.token))
        assert fp in storage.deleted


class TestFileManagerDeletion:
    def test_delete_file_deletes_metadata_and_physical(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="job-del", filename="f4", ttl_minutes=10)
        repo.save(f)

        ok = mgr.delete_file(str(f.token), delete_physical=True)
        assert ok is True
        assert not repo.exists(str(f.token))
        assert fp in storage.deleted

    def test_delete_file_only_metadata_when_flag_false(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="job-del2", filename="f5", ttl_minutes=10)
        repo.save(f)

        ok = mgr.delete_file(str(f.token), delete_physical=False)
        assert ok is True
        assert not repo.exists(str(f.token))
        assert fp not in storage.deleted

    def test_delete_file_by_job_id_handles_physical_error_gracefully(self, tmp_path):
        class ErrorStorage(DummyStorageRepo):
            def delete(self, file_path: str) -> bool:
                raise IOError("fs error")

        repo = InMemoryFileRepo()
        storage = ErrorStorage()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="job-del3", filename="f6", ttl_minutes=10)
        repo.save(f)

        ok = mgr.delete_file_by_job_id("job-del3")
        assert ok is True
        assert not repo.exists(str(f.token))

    def test_delete_file_by_job_id_returns_false_when_missing(self):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)
        assert mgr.delete_file_by_job_id("unknown") is False


class TestFileManagerCleanup:
    def test_cleanup_expired_files_deletes_all_and_counts(self, tmp_path):
        repo = InMemoryFileRepo()

        # one storage that fails for one file to hit exception path
        class SometimesErrorStorage(DummyStorageRepo):
            def delete(self, file_path: str) -> bool:
                if file_path.endswith("b.bin"):
                    raise IOError("boom")
                return super().delete(file_path)

        storage = SometimesErrorStorage()
        mgr = FileManager(repo, storage)

        fp_a = create_temp_file(tmp_path, name="a.bin")
        fp_b = create_temp_file(tmp_path, name="b.bin")
        f1 = DownloadedFile.create(fp_a, job_id="ja", filename="fa", ttl_minutes=0)
        f1.expires_at = datetime.utcnow() - timedelta(seconds=1)
        f2 = DownloadedFile.create(fp_b, job_id="jb", filename="fb", ttl_minutes=0)
        f2.expires_at = datetime.utcnow() - timedelta(seconds=1)
        repo.save(f1)
        repo.save(f2)

        cleaned = mgr.cleanup_expired_files()
        assert cleaned == 2
        # both metadata removed
        assert not repo.exists(str(f1.token))
        assert not repo.exists(str(f2.token))


class TestFileManagerInfoAndValidation:
    def test_get_download_url_uses_token(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="jid", filename="fn", ttl_minutes=10)
        repo.save(f)
        url = mgr.get_download_url(str(f.token), base_url="/downloads")
        assert url.endswith(str(f.token))

    def test_validate_token_true_for_existing_not_expired(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="jid2", filename="fn2", ttl_minutes=10)
        repo.save(f)
        assert mgr.validate_token(str(f.token)) is True

    def test_validate_token_false_on_repo_error(self, monkeypatch):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        def boom(token):
            raise RuntimeError("repo failed")

        monkeypatch.setattr(repo, "get_by_token", boom)
        assert mgr.validate_token("whatever") is False

    def test_get_file_info_contains_expected_fields(self, tmp_path):
        repo = InMemoryFileRepo()
        storage = DummyStorageRepo()
        mgr = FileManager(repo, storage)

        fp = create_temp_file(tmp_path)
        f = DownloadedFile.create(fp, job_id="jid3", filename="fn3", ttl_minutes=10)
        repo.save(f)
        info = mgr.get_file_info(str(f.token))
        assert info["token"] == str(f.token)
        assert info["filename"] == "fn3"
        assert "download_url" in info
        assert isinstance(info["remaining_seconds"], int)
