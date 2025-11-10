"""
Job Management Domain

Manages asynchronous download jobs, progress tracking, and status updates.
"""

from .entities import DownloadJob
from .value_objects import JobStatus, JobProgress
from .services import JobManager, JobNotFoundError, JobStateError
from .repositories import JobRepository

__all__ = [
    'DownloadJob',
    'JobStatus',
    'JobProgress',
    'JobManager',
    'JobRepository',
    'JobNotFoundError',
    'JobStateError'
]
