"""
Logging Event Handler

Infrastructure event handler for logging domain events.
Subscribes to domain events and logs them appropriately.
Domain layer remains unaware of logging infrastructure.
"""

import logging

from src.domain.events import (
    DomainEvent,
    FormatExtractionCompletedEvent,
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent,
    JobStartedEvent,
    MetadataExtractionFailedEvent,
    VideoDownloadCompletedEvent,
    VideoDownloadFailedEvent,
    VideoDownloadProgressEvent,
    VideoDownloadStartedEvent,
    VideoMetadataExtractedEvent,
)


class LoggingEventHandler:
    """
    Infrastructure event handler for logging domain events.

    Subscribes to domain events and logs them appropriately.
    Domain layer remains unaware of logging infrastructure.
    """

    def __init__(self, logger: logging.Logger):
        """
        Initialize with logger instance.

        Args:
            logger: Python logging.Logger instance
        """
        self.logger = logger

    def handle(self, event: DomainEvent) -> None:
        """
        Handle domain event by logging it.

        Args:
            event: Domain event to log
        """
        try:
            if isinstance(event, VideoMetadataExtractedEvent):
                self._handle_metadata_extracted(event)
            elif isinstance(event, MetadataExtractionFailedEvent):
                self._handle_extraction_failed(event)
            elif isinstance(event, FormatExtractionCompletedEvent):
                self._handle_format_extraction(event)
            elif isinstance(event, VideoDownloadStartedEvent):
                self._handle_download_started(event)
            elif isinstance(event, VideoDownloadProgressEvent):
                self._handle_download_progress(event)
            elif isinstance(event, VideoDownloadCompletedEvent):
                self._handle_download_completed(event)
            elif isinstance(event, VideoDownloadFailedEvent):
                self._handle_download_failed(event)
            elif isinstance(event, JobStartedEvent):
                self._handle_job_started(event)
            elif isinstance(event, JobProgressUpdatedEvent):
                self._handle_job_progress(event)
            elif isinstance(event, JobCompletedEvent):
                self._handle_job_completed(event)
            elif isinstance(event, JobFailedEvent):
                self._handle_job_failed(event)
            else:
                self.logger.debug(
                    f"Unhandled event: {event.__class__.__name__} "
                    f"(aggregate_id={event.aggregate_id})"
                )
        except Exception as e:
            # Log handler errors but don't fail the operation
            self.logger.error(
                f"Error in logging event handler for {event.__class__.__name__}: {e}",
                exc_info=True,
            )

    def _handle_metadata_extracted(self, event: VideoMetadataExtractedEvent) -> None:
        """Log successful metadata extraction."""
        self.logger.info(
            f"Video metadata extracted: {event.video_id} - {event.title} "
            f"(duration: {event.duration}s)"
        )

    def _handle_extraction_failed(self, event: MetadataExtractionFailedEvent) -> None:
        """Log failed metadata extraction."""
        self.logger.error(
            f"Metadata extraction failed for {event.url}: {event.error_message}"
        )

    def _handle_format_extraction(self, event: FormatExtractionCompletedEvent) -> None:
        """Log format extraction completion."""
        self.logger.info(f"Extracted {event.format_count} formats for {event.url}")

    def _handle_download_started(self, event: VideoDownloadStartedEvent) -> None:
        """Log video download start."""
        self.logger.info(
            f"Video download started: job_id={event.aggregate_id}, "
            f"video_id={event.video_id}, format_id={event.format_id}"
        )

    def _handle_download_progress(self, event: VideoDownloadProgressEvent) -> None:
        """Log video download progress."""
        self.logger.debug(
            f"Video download progress: job_id={event.aggregate_id}, "
            f"video_id={event.video_id}, {event.percentage:.1f}% "
            f"({event.downloaded_bytes}/{event.total_bytes} bytes)"
        )

    def _handle_download_completed(self, event: VideoDownloadCompletedEvent) -> None:
        """Log video download completion."""
        self.logger.info(
            f"Video download completed: job_id={event.aggregate_id}, "
            f"video_id={event.video_id}, file_path={event.file_path}, "
            f"file_size={event.file_size} bytes"
        )

    def _handle_download_failed(self, event: VideoDownloadFailedEvent) -> None:
        """Log video download failure."""
        self.logger.error(
            f"Video download failed: job_id={event.aggregate_id}, "
            f"video_id={event.video_id}, error={event.error_message}"
        )

    def _handle_job_started(self, event: JobStartedEvent) -> None:
        """Log job start."""
        self.logger.info(
            f"Job started: job_id={event.aggregate_id}, "
            f"url={event.url}, format_id={event.format_id}"
        )

    def _handle_job_progress(self, event: JobProgressUpdatedEvent) -> None:
        """Log job progress update."""
        progress_data = event.progress.to_dict()
        self.logger.debug(
            f"Job progress: job_id={event.aggregate_id}, "
            f"percent={progress_data.get('percentage', 0)}%"
        )

    def _handle_job_completed(self, event: JobCompletedEvent) -> None:
        """Log job completion."""
        self.logger.info(
            f"Job completed: job_id={event.aggregate_id}, "
            f"download_url={event.download_url}, expire_at={event.expire_at}"
        )

    def _handle_job_failed(self, event: JobFailedEvent) -> None:
        """Log job failure."""
        self.logger.warning(
            f"Job failed: job_id={event.aggregate_id}, "
            f"error={event.error_message}, category={event.error_category}"
        )
