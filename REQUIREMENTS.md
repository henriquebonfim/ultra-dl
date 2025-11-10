# UltraDL - Requirements Specification

## Introduction

This document specifies the requirements for the UltraDL YouTube video downloader application. UltraDL is a web-based application that allows users to download YouTube videos in various resolutions up to 8K, with real-time progress tracking, automatic expiration handling, and comprehensive error management.

## Glossary

- **System**: The UltraDL application (frontend + backend + infrastructure)
- **User**: End user accessing the web application
- **Job**: A download task with unique identifier and status tracking
- **Token**: Secure identifier for file access with time-limited validity
- **Expiration**: 10-minute time limit after which download links become invalid
- **WebSocket**: Real-time bidirectional communication protocol
- **Polling**: HTTP-based periodic status checking mechanism
- **Celery**: Distributed task queue for asynchronous processing
- **Redis**: In-memory data store for job persistence and caching
- **GCS**: Google Cloud Storage for production file storage
- **yt-dlp**: YouTube video extraction and download library

## Functional Requirements

### FR-1: Video URL Validation

**User Story**: As a user, I want to validate YouTube URLs before processing so that I receive immediate feedback on invalid inputs.

**Requirements**:

1.1. WHEN the user enters a URL, THE system SHALL validate the URL format against YouTube URL patterns.

1.2. IF the URL format is invalid, THEN THE system SHALL display an error message within 100 milliseconds.

1.3. THE system SHALL accept youtube.com, youtu.be, and m.youtube.com URL formats.

1.4. THE system SHALL extract video metadata within 5 seconds of valid URL submission.

**Acceptance Criteria**:
- Valid YouTube URLs are accepted and processed
- Invalid URLs show immediate error feedback
- URL validation completes within 100ms
- Metadata extraction completes within 5 seconds

### FR-2: Video Format Selection

**User Story**: As a user, I want to see all available video formats so that I can choose my preferred quality and file size.

**Requirements**:

2.1. WHEN video metadata is retrieved, THE system SHALL display all available formats grouped by type.

2.2. THE system SHALL group formats into "Video+Audio", "Video Only", and "Audio Only" categories.

2.3. THE system SHALL sort formats by resolution height in descending order within each group.

2.4. THE system SHALL display format details including resolution, codec, and file size.

2.5. THE system SHALL show quality labels (Ultra, Excellent, Great, Good, Standard) based on resolution.

**Acceptance Criteria**:
- All available formats are displayed
- Formats are grouped and sorted correctly
- Format details are accurate and complete
- Quality labels match resolution ranges

### FR-3: Asynchronous Download Processing

**User Story**: As a user, I want downloads to process in the background so that I can track progress without blocking the interface.

**Requirements**:

3.1. WHEN the user initiates a download, THE system SHALL create a job with unique identifier.

3.2. THE system SHALL return the job identifier within 500 milliseconds of download initiation.

3.3. THE system SHALL process downloads asynchronously using Celery task queue.

3.4. THE system SHALL update job progress at intervals not exceeding 1 second.

3.5. THE system SHALL support concurrent downloads from multiple users.

**Acceptance Criteria**:
- Job creation completes within 500ms
- Downloads process in background
- Progress updates occur at least every second
- Multiple concurrent downloads are supported

### FR-4: Real-Time Progress Tracking

**User Story**: As a user, I want to see real-time download progress so that I know how long to wait.

**Requirements**:

4.1. THE system SHALL attempt WebSocket connection for real-time updates.

4.2. IF WebSocket connection fails within 5 seconds, THEN THE system SHALL fall back to HTTP polling.

4.3. WHILE downloading, THE system SHALL display percentage, phase, speed, and estimated time remaining.

4.4. THE system SHALL update progress display at intervals not exceeding 1 second.

4.5. WHEN download completes, THE system SHALL display download button within 500 milliseconds.

**Acceptance Criteria**:
- WebSocket connection attempted first
- Automatic fallback to polling within 5 seconds
- Progress metrics displayed accurately
- Download button appears immediately on completion

### FR-5: Download Expiration Management

**User Story**: As a user, I want to know when my download will expire so that I can download it in time.

**Requirements**:

5.1. WHEN download completes, THE system SHALL set expiration time to 10 minutes.

5.2. THE system SHALL display countdown timer showing time remaining.

5.3. THE system SHALL update countdown display every 1 second.

5.4. WHEN countdown reaches zero, THE system SHALL trigger expiration animation.

5.5. THE system SHALL display expiration notification for 10 seconds.

5.6. WHEN download expires, THE system SHALL disconnect WebSocket connection.

5.7. WHEN download expires, THE system SHALL stop polling requests.

5.8. WHEN download expires, THE system SHALL delete file from storage.

**Acceptance Criteria**:
- Expiration set to exactly 10 minutes
- Countdown updates every second
- Animation plays on expiration
- Notification displayed for 10 seconds
- All connections closed on expiration
- Files deleted automatically

### FR-6: Download Cancellation

**User Story**: As a user, I want to cancel active downloads so that I can stop unwanted downloads.

**Requirements**:

6.1. WHILE job status is pending or processing, THE system SHALL display cancel button.

6.2. WHEN user clicks cancel, THE system SHALL revoke Celery task within 2 seconds.

6.3. WHEN user clicks cancel, THE system SHALL delete job record from Redis.

6.4. WHEN user clicks cancel, THE system SHALL display cancellation confirmation.

6.5. THE system SHALL terminate running download processes using SIGKILL signal.

**Acceptance Criteria**:
- Cancel button visible during pending/processing
- Task revocation completes within 2 seconds
- Job record deleted from Redis
- Confirmation message displayed
- Download process terminated

### FR-7: Video Metadata Display

**User Story**: As a user, I want to see video details so that I can verify I'm downloading the correct video.

**Requirements**:

7.1. WHEN download completes, THE system SHALL display video metadata card.

7.2. THE system SHALL display video title with truncation for titles exceeding 60 characters.

7.3. THE system SHALL display channel name, duration, resolution, format, and file size.

7.4. THE system SHALL format duration as HH:MM:SS for videos exceeding 1 hour.

7.5. THE system SHALL format duration as MM:SS for videos under 1 hour.

7.6. THE system SHALL format file size in MB for sizes under 1024 MB.

7.7. THE system SHALL format file size in GB for sizes exceeding 1024 MB.

**Acceptance Criteria**:
- Metadata card displayed on completion
- All metadata fields populated
- Long titles truncated with tooltip
- Duration formatted correctly
- File size formatted with 2 decimal places

### FR-8: Error Handling and User Feedback

**User Story**: As a user, I want clear error messages so that I understand what went wrong and how to fix it.

**Requirements**:

8.1. WHEN an error occurs, THE system SHALL categorize the error type.

8.2. THE system SHALL display user-friendly error messages with actionable guidance.

8.3. THE system SHALL show error notifications for at least 5 seconds.

8.4. IF error is retryable, THEN THE system SHALL display retry button.

8.5. THE system SHALL handle network errors with automatic retry up to 3 attempts.

8.6. THE system SHALL handle rate limiting with exponential backoff.

**Acceptance Criteria**:
- Errors categorized correctly
- Messages are user-friendly
- Notifications visible for 5+ seconds
- Retry button shown for retryable errors
- Network errors retry automatically
- Rate limiting handled gracefully

### FR-9: File Storage and Delivery

**User Story**: As a user, I want secure file access so that my downloads are protected.

**Requirements**:

9.1. THE system SHALL generate secure tokens for file access.

9.2. THE system SHALL create signed URLs with 10-minute expiration.

9.3. WHERE GCS is configured, THE system SHALL upload files to cloud storage.

9.4. WHERE GCS is not configured, THE system SHALL store files locally.

9.5. THE system SHALL serve files via streaming for efficient delivery.

9.6. WHEN token expires, THE system SHALL return 410 Gone status.

**Acceptance Criteria**:
- Tokens are cryptographically secure
- Signed URLs expire after 10 minutes
- GCS used when configured
- Local storage used as fallback
- Files streamed efficiently
- Expired tokens return 410

### FR-10: Rate Limiting (Production Only)

**User Story**: As a system administrator, I want rate limiting so that the service is not abused.

**Requirements**:

10.1. WHERE environment is production, THE system SHALL enforce rate limits.

10.2. THE system SHALL limit resolution requests to 20 per minute per IP.

10.3. THE system SHALL limit download requests to 10 per minute per IP.

10.4. THE system SHALL limit status polling to 30 per minute per IP.

10.5. THE system SHALL limit total requests to 200 per day per IP.

10.6. WHEN rate limit is exceeded, THE system SHALL return 429 status code.

10.7. WHERE environment is development, THE system SHALL disable rate limiting.

**Acceptance Criteria**:
- Rate limits enforced in production
- Limits match specified values
- 429 status returned on excess
- Rate limiting disabled in development

## Non-Functional Requirements

### NFR-1: Performance

1.1. THE system SHALL respond to API requests within 500 milliseconds for 95% of requests.

1.2. THE system SHALL support at least 10 concurrent downloads.

1.3. THE system SHALL update progress at intervals not exceeding 1 second.

1.4. THE system SHALL complete metadata extraction within 5 seconds.

### NFR-2: Reliability

2.1. THE system SHALL maintain 99% uptime during business hours.

2.2. THE system SHALL automatically retry failed operations up to 3 times.

2.3. THE system SHALL gracefully handle WebSocket disconnections.

2.4. THE system SHALL persist job data with 1-hour TTL in Redis.

### NFR-3: Scalability

3.1. THE system SHALL support horizontal scaling of Celery workers.

3.2. THE system SHALL use connection pooling with maximum 20 connections.

3.3. THE system SHALL implement distributed locking for atomic operations.

3.4. THE system SHALL support multiple concurrent users without degradation.

### NFR-4: Security

4.1. THE system SHALL generate cryptographically secure tokens (32 bytes).

4.2. THE system SHALL use HMAC signatures for URL signing.

4.3. THE system SHALL sanitize file names to prevent path traversal.

4.4. THE system SHALL validate all user inputs before processing.

### NFR-5: Maintainability

5.1. THE system SHALL follow Domain-Driven Design architecture.

5.2. THE system SHALL maintain separation between domain, application, and infrastructure layers.

5.3. THE system SHALL use repository pattern for data access abstraction.

5.4. THE system SHALL include comprehensive error logging.

### NFR-6: Usability

6.1. THE system SHALL provide visual feedback for all user actions within 100 milliseconds.

6.2. THE system SHALL use animations with duration not exceeding 2 seconds.

6.3. THE system SHALL display loading indicators for operations exceeding 500 milliseconds.

6.4. THE system SHALL support mobile devices with responsive design.

## Constraints

1. The system SHALL use Python 3.9+ for backend implementation.
2. The system SHALL use React 18+ for frontend implementation.
3. The system SHALL use Redis 6+ for data persistence.
4. The system SHALL use Celery 5+ for task queue.
5. The system SHALL require ffmpeg for video processing.
6. The system SHALL use yt-dlp for YouTube integration.
7. The system SHALL support Docker containerization.
8. The system SHALL use Flask for REST API implementation.

## Assumptions

1. Users have stable internet connection for downloads.
2. YouTube API and yt-dlp remain functional.
3. Redis server is available and accessible.
4. Sufficient disk space is available for temporary files.
5. ffmpeg is installed and accessible on system PATH.
6. Users access the application via modern web browsers.
