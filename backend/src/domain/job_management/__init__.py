"""
Job Management Domain

Manages asynchronous download jobs, progress tracking, and status updates.
"""

from .entities import DownloadJob, JobArchive
from .value_objects import JobStatus, JobProgress
from .services import JobManager, JobNotFoundError, JobStateError
from .repositories import JobRepository, IJobArchiveRepository

__all__ = [
    'DownloadJob',
    'JobArchive',
    'JobStatus',
    'JobProgress',
    'JobManager',
    'JobRepository',
    'IJobArchiveRepository',
    'JobNotFoundError',
    'JobStateError'
]
