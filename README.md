# UltraDL - YouTube Video Downloader

## Overview

UltraDL is a web-based YouTube video downloader application that allows users to download videos in various resolutions up to 8K. The application consists of a React-based frontend with a Flask/Python backend that leverages yt-dlp for video processing.

**Recent Updates:**

*Cancel Download Fix & Enhanced UX (Latest):*
- **Fixed 409 Conflict error when canceling downloads**: DELETE endpoint now accepts pending/processing jobs for cancellation
- Backend changes:
  - Removed "only completed jobs can be deleted" restriction from DELETE /api/v1/jobs/{job_id}
  - Added Celery task revocation (SIGKILL) when canceling pending/processing jobs
  - Updated API documentation to reflect cancel + delete functionality
  - Endpoint now handles both cancellation (pending/processing) and deletion (completed/failed)
- Frontend changes:
  - Updated handleDeleteJob to show appropriate messages ("cancelled" vs "deleted")
  - Different toast notifications based on job status
  - Improved error handling for delete/cancel operations
- Users can now cancel downloads at any stage without errors

*Expiration Time Display Fix & Enhanced UX (Previous):*
- **Fixed incorrect expiration countdown**: Frontend now correctly displays ~8 minutes remaining instead of 4+ hours
- Root cause: Frontend was calculating time from `expire_at` timestamp (timezone issue) instead of using `time_remaining` from API
- Solution: Added `time_remaining` field to frontend types and updated ProgressTracker to use server-calculated seconds
- Frontend now counts down from the server-provided `time_remaining` value (in seconds) for accurate display
- Improved countdown logic with proper hours/minutes/seconds formatting
- **Added automatic WebSocket disconnect on expiration**: WebSocket connection is now automatically closed when download expires
- **Fixed infinite polling issue**: Polling now properly stops when download expires or is completed
- **Added explosion animation on expiration**: Card animates with scale, rotation, and blur effects when download expires
  - 2-second explosion animation with multiple keyframes
  - Card automatically hides after animation completes
  - Smooth visual feedback for expiration event
- **Enhanced expiration alert**: Users see a prominent toast notification with emoji (💥 Download Expired!)
  - Clear message explaining file deletion and suggesting new download if needed
  - 10-second display duration for visibility
  - Automatic cleanup of job state after animation
- **Added video metadata display**: Download progress now shows detailed video information including:
  - Video title (with truncation for long titles)
  - Channel name (uploader)
  - Video duration (formatted as HH:MM:SS or MM:SS)
  - Selected resolution (e.g., 1080p, 720p)
  - File format (MP4, WebM, etc.)
  - File size (in MB or GB when available)
- Metadata displayed in a clean card below the download button for better user context

*Download Timeout Fix (Previous):*
- **Fixed download timeout error**: Downloads with slow internet connections no longer fail with generic "System Error"
- Added new `DOWNLOAD_TIMEOUT` error category with user-friendly message explaining slow connection issues
- Increased Celery task time limits from 10 minutes to 30 minutes (configurable via environment variables)
- Added specific handling for `SoftTimeLimitExceeded` exception to provide actionable error messages
- Users now see: "Download Timeout: The download took too long to complete. Try selecting a lower quality format."
- Time limits configurable via `CELERY_TASK_SOFT_TIME_LIMIT` and `CELERY_TASK_TIME_LIMIT` environment variables

*Frontend UX Improvements & Bug Fixes (Previous):*
- Added cancel button during download progress (pending and processing states)
- Changed error display from Card component to toast notifications for better UX
- Fixed download button CSS to match project design (font-semibold instead of font-bold)
- Implemented input/selection blocking during active downloads to prevent conflicts
- Added request debouncing to prevent multiple simultaneous API calls
- Enhanced state management with isDownloading flag for better UI control
- **Fixed expiration time bug**: GCS downloads now correctly set 10-minute expiration time (was showing 4h+ because expire_at wasn't being set for GCS uploads)
- **Rate limiting improvements**: 
  - Disabled rate limiting in development mode (FLASK_ENV=development) for easier testing
  - Rate limits only apply in production (FLASK_ENV=production)
  - Added 30 requests/minute limit for job status polling in production

*Code Cleanup (Previous):*
- Removed unused frontend hooks (useWebSocket, useJobStatus, useApiError) - integrated into useJobStatusWithWebSocket
- Removed unused backend services (FileService, UnifiedFileService) - functionality integrated into JobService
- Removed unused npm packages (date-fns, react-day-picker, recharts, vaul, embla-carousel-react, input-otp, cmdk, react-resizable-panels)
- Removed example/demo code (ErrorHandlingExample) and unused components (ErrorMessage, App.css)
- Fixed TypeScript linting issues in custom hooks (prefer-const, explicit types)
- All shadcn/ui components retained for future extensibility
- Build and tests passing successfully

**Core Functionality:**
- URL validation for YouTube videos
- Resolution/format selection from available video formats
- Video downloading with format/resolution preferences
- Support for high-resolution videos (4K/8K)

**Technology Stack:**
- Frontend: React + TypeScript + Vite
- UI Framework: shadcn/ui with Radix UI primitives
- Styling: Tailwind CSS with custom dark theme
- Backend: Flask (Python)
- Video Processing: yt-dlp + ffmpeg
- State Management: TanStack Query (React Query)

## Documentation

- **[REQUIREMENTS.md](REQUIREMENTS.md)** - Detailed requirements specification using EARS (Easy Approach to Requirements Syntax)
- **[DESIGN.md](DESIGN.md)** - System architecture and design decisions
- **[TASKS.md](TASKS.md)** - Implementation tasks and progress tracking
- **[environment-variables.md](environment-variables.md)** - Environment configuration guide
- **[DOCKER_DEBUG.md](DOCKER_DEBUG.md)** - Docker debugging and troubleshooting
- **[CLEANUP_SUMMARY.md](CLEANUP_SUMMARY.md)** - Code cleanup and maintenance notes

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Build System:**
- Vite as the build tool and development server
- TypeScript for type safety with relaxed strict mode settings
- React 18 with React Router for client-side routing
- SWC plugin for fast React refresh during development

**Component Structure:**
- Component-based architecture using React functional components
- shadcn/ui design system for consistent UI components
- Radix UI primitives for accessible, unstyled components
- Framer Motion for animations and transitions
- Path aliases configured (@/ maps to ./src/) for clean imports

**Styling Approach:**
- Tailwind CSS with CSS variables for theming
- Dark mode as the primary theme (defined in index.css)
- Custom color system using HSL values for design tokens
- CSS custom properties for gradients and shadows
- Responsive design with mobile-first breakpoints

**State Management:**
- TanStack Query (React Query) for server state and API calls
- Local component state with React hooks
- No global state management library (Redux/Zustand) currently implemented

**Key Pages:**
- **Index (/)** - Main application page orchestrating the complete download workflow
  - Manages application state for URL validation, format selection, and download progress
  - Coordinates component communication through callback functions and props
  - Implements responsive layout with Tailwind CSS (max-w-7xl container, mobile-first design)
  - Flow: URL Input → Video Preview → Format Selection → Download → Progress Tracking
  - State management: isValidated, selectedResolution, availableResolutions, videoMeta, currentUrl
  - Conditional rendering: Components appear progressively as user completes each step
  - Integration with all major components: UrlInput, VideoPreview, ResolutionPicker, DownloadButton, ProgressTracker
  - Ad placement support with AdBanner components (top and bottom positions)
  - Full-page layout with Header and Footer components
- **NotFound (*)** - Catch-all 404 error page

**Component Organization:**
- UI components in src/components/ui/ (shadcn/ui library)
- Feature components in src/components/ (AdBanner, DownloadButton, Footer, Header, ResolutionPicker, UrlInput, VideoPreview, ProgressTracker)
- Hooks in src/hooks/ (use-mobile, use-toast, useJobStatus, useJobStatusWithWebSocket, useWebSocket)
- Utility functions in src/lib/utils.ts

**Custom Hooks:**
- **useJobStatus** - Polling-based job status tracking with 5-second intervals
  - Automatic polling stop when job completes or fails
  - Rate limit handling with exponential backoff
  - Retry logic for transient errors (network, 5xx)
  - Returns job status, progress, download URL, and error information
- **useWebSocket** - Socket.IO client wrapper for real-time updates
  - Automatic connection management with reconnection support
  - Event handlers for progress, completion, and failure
  - Subscription to job-specific updates
  - Graceful cleanup on unmount
- **useJobStatusWithWebSocket** - Enhanced job status hook with WebSocket support
  - Attempts WebSocket connection first for real-time updates
  - Automatic fallback to polling if WebSocket fails (5-second timeout)
  - Unified interface for both connection methods
  - Error toast notifications with categorized error messages
  - Connection method indicator (websocket/polling/none)

**VideoPreview Component:**
- Displays video thumbnail with interactive play button overlay
- Shows video metadata including title, uploader (channel name), and formatted duration
- Supports YouTube embed playback when thumbnail is clicked
- Graceful error handling for unavailable or restricted videos
- Responsive design with aspect ratio preservation
- Framer Motion animations for smooth appearance
- Duration formatting (HH:MM:SS or MM:SS based on video length)
- Fallback thumbnail loading from multiple YouTube CDN sources
- Hover effects and transitions for enhanced user experience

**UrlInput Component:**
- YouTube URL validation with regex pattern matching
- Client-side validation for empty and invalid URLs
- Direct API integration with POST /api/v1/videos/resolutions endpoint
- Loading state management during API calls
- Error handling with toast notifications for user feedback
- Success callback with video metadata and available formats
- Keyboard support (Enter key to submit)
- Visual feedback for invalid URLs with border color changes
- Framer Motion animations for smooth appearance

**ResolutionPicker Component:**
- Intelligent format grouping by type (Video+Audio, Video Only, Audio Only)
- Automatic sorting by resolution height in descending order within each group
- Format cards displaying resolution, codec information, and filesize
- Human-readable filesize formatting (MB/GB conversion)
- Quality labels based on resolution (Ultra, Excellent, Great, Good, Standard)
- Detailed codec information tooltips (video/audio codec details)
- Compatibility notes for different file formats (MP4, WebM, MKV, M4A)
- Visual selection feedback with checkmark indicator
- Hover effects and scale animations for enhanced interactivity
- Info tooltips showing codec details, compatibility, and filesize
- Responsive grid layout (1 column mobile, 2 columns tablet, 3 columns desktop)
- Framer Motion animations with staggered appearance
- Icon indicators for format types (Video, FileVideo, Music icons)
- Group descriptions explaining each format type
- Filters out invalid formats (no video and no audio)

**ProgressTracker Component:**
- Real-time progress tracking with visual progress bar and percentage display
- Job status display (pending, processing, completed, failed) with appropriate icons
- Download speed and ETA (estimated time remaining) during processing
- Cancel button for pending downloads to abort before processing starts
- Delete button for completed downloads to manually remove files from server
- Retry button for failed downloads to start a new download attempt
- File expiration countdown showing time remaining before automatic deletion
- WebSocket support with automatic fallback to polling for real-time updates
- Connection method indicator (WebSocket or polling) for transparency
- Error display with user-friendly messages and actionable guidance
- Clickable download button when job completes successfully
- Framer Motion animations for smooth state transitions
- Responsive design with mobile-friendly layout
- Automatic cleanup on component unmount to prevent memory leaks

**Error Handling System:**
- **ErrorCard Component** - Comprehensive error display with title, message, and actionable guidance
  - Supports both alert and card variants for different use cases
  - Retry and dismiss actions for user control
  - Framer Motion animations for smooth appearance
  - Consistent styling with destructive variant
- **ErrorMessage Component** - Simple inline error messages for form validation
  - Animated appearance with height transitions
  - Icon indicator for visual feedback
- **Error Utilities** (`lib/errors.ts`) - Centralized error handling logic
  - `ErrorCategory` enum matching backend error categories
  - `parseApiError()` - Parses API responses and extracts error information
  - `formatErrorForToast()` - Formats errors for toast notifications
  - `isRetryableError()` - Determines if errors can be retried
  - User-friendly error messages with actionable guidance for all error types
- **useApiError Hook** - Custom hook for consistent error handling
  - Error state management
  - Automatic toast notifications
  - Clear error functionality
- **Error Categories Supported:**
  - Invalid URL - YouTube URL validation errors
  - Video Unavailable - Private, deleted, or restricted videos
  - Format Not Supported - Unavailable format selections
  - Download Failed - General download errors
  - Download Timeout - Slow connection or large file timeout
  - File Too Large - Size limit exceeded
  - Rate Limited - Too many requests
  - System Error - Unexpected errors
  - Job Not Found - Missing or expired jobs
  - Invalid Request - Malformed requests
  - Network Error - Connection issues
  - File Not Found - Missing files
  - File Expired - Expired download links
  - Geo Blocked - Region-restricted content
  - Login Required - Authentication needed
  - Platform Rate Limited - YouTube rate limiting

### Backend Architecture

**Framework:**
- Flask application with Domain-Driven Design (DDD) architecture
- Flask-CORS enabled for cross-origin requests from the frontend
- Flask-Limiter with Redis storage for rate limiting
- Production-ready with proper error handling and monitoring

**Core Infrastructure:**
- **Redis** - Connection pooling with configurable max connections (default: 20)
- **Celery** - Distributed task queue with Redis broker and result backend
- **Distributed Locking** - Redis-based locks for atomic operations
- **Rate Limiting** - Flask-Limiter with Redis storage (200/day, 50/hour default)
- **Connection Management** - Automatic retry on timeout with socket keepalive

**API Endpoints:**
- `/api/v1/videos/resolutions` (POST) - Fetches available video formats/resolutions for a given YouTube URL
  - Rate limit: 20 requests per minute per IP (production only)
  - Returns video metadata (title, uploader, duration, thumbnail) and available formats
  - Validates YouTube URL format and handles yt-dlp errors with user-friendly messages
- `/api/v1/downloads/` (POST) - Creates an asynchronous download job and returns job_id
  - Rate limit: 10 requests per minute per IP (production only)
  - Validates URL and format_id before creating job
  - Enqueues Celery task for background processing
  - Returns HTTP 202 Accepted with job_id
- `/api/v1/jobs/{job_id}` (GET) - Polls job status and progress
  - Rate limit: 30 requests per minute per IP (production only, supports 5-second polling)
  - Returns job status (pending, processing, completed, failed)
  - Includes progress percentage, phase, speed, and ETA
  - Provides download_url, expire_at timestamp, and time_remaining when job completes
  - Returns HTTP 404 if job not found
- `/api/v1/jobs/{job_id}` (DELETE) - Deletes a completed job and its associated file
  - Only completed jobs can be deleted
  - Removes job record from Redis and file from storage
  - Returns HTTP 204 No Content on success
  - Returns HTTP 409 Conflict if job not completed
- `/api/v1/downloads/file/{token}` (GET) - Downloads file using secure token
  - Validates token and checks expiration (10-minute TTL)
  - Serves file via GCS signed URL or local streaming
  - Returns HTTP 410 Gone if token expired
  - Returns HTTP 404 if file not found
- `/health` (GET) - Health check endpoint for backend, Redis, Celery, GCS, and SocketIO status
  - Exempt from rate limiting
  - Returns HTTP 200 with status "ok" if all critical services available
  - Returns HTTP 503 with status "degraded" if any critical service unavailable
  - Reports optional services (GCS, SocketIO) as "not_configured" when disabled

**WebSocket Support (Optional):**
- **Real-Time Progress Updates** - Socket.IO integration for instant progress notifications
  - Enabled via `SOCKETIO_ENABLED=true` environment variable (default: true)
  - Graceful fallback to polling if WebSocket connection fails
  - Redis message queue for multi-worker support
- **WebSocket Events:**
  - `connect` - Client connection established
  - `disconnect` - Client disconnection
  - `subscribe_job` - Subscribe to job progress updates for specific job_id
  - `unsubscribe_job` - Unsubscribe from job updates
  - `cancel_job` - Cancel a pending or processing job
  - `job_progress` - Real-time progress updates (percentage, phase, speed, eta)
  - `job_completed` - Job completion notification with download URL and expiration
  - `job_failed` - Job failure notification with error details
  - `job_cancelled` - Job cancellation confirmation
  - `ping/pong` - Connection health check
- **Connection Details:**
  - Endpoint: `ws://localhost/socket.io/`
  - CORS enabled for all origins (configure for production)
  - Automatic reconnection with exponential backoff
  - 60-second ping timeout, 25-second ping interval
- **Benefits:**
  - Reduces server load by eliminating constant polling
  - Instant progress updates for better user experience
  - Supports multiple concurrent users efficiently
  - Maintains backward compatibility with polling method

**API Documentation:**
- **Interactive Swagger UI**: `http://localhost/api/v1/docs`
  - Full API documentation with request/response examples
  - Try-it-out functionality for testing endpoints directly in browser
  - Organized into namespaces: videos, jobs, downloads, system
  - Comprehensive model definitions with field descriptions
  - Real-time API testing without external tools
- **OpenAPI Specification**: `http://localhost/api/v1/swagger.json`
  - OpenAPI 2.0 (Swagger) specification
  - Machine-readable API contract
  - Can be imported into API clients (Postman, Insomnia, etc.)
  - Automated generation via Flask-RESTX
- **Documentation Features**:
  - All endpoints include comprehensive request/response models
  - Parameter descriptions with examples and validation rules
  - Response codes with detailed explanations (200, 202, 400, 404, 409, 410, 429, 503)
  - Error responses follow consistent format with error category and actionable guidance
  - Rate limiting information for each endpoint (20/min for resolutions, 10/min for downloads)
  - Health check endpoint documentation with service status details
- **Documented Endpoints**:
  - `POST /api/v1/videos/resolutions` - Get available video formats
  - `POST /api/v1/downloads/` - Initiate download job
  - `GET /api/v1/jobs/{job_id}` - Get job status and progress
  - `DELETE /api/v1/jobs/{job_id}` - Delete completed job
  - `GET /api/v1/downloads/file/{token}` - Download file by token
  - `GET /api/v1/system/health` - System health check

**Video Processing:**
- **Domain-Driven Design** - Clean architecture with domain, application, and infrastructure layers
- **Format Extraction** - yt-dlp integration for metadata and format extraction with comprehensive error handling
- **Format Grouping** - Automatic grouping by type (Video+Audio, Video Only, Audio Only)
- **Format Sorting** - Sorted by resolution height in descending order within each group
- **Quality Labels** - Automatic quality label calculation (Ultra, Excellent, Great, Good, Standard)
- **Filesize Handling** - Intelligent filesize extraction from multiple yt-dlp fields (filesize, filesize_approx, calculated from bitrate)
- **URL Validation** - YouTube URL validation with support for multiple URL formats (youtube.com, youtu.be, m.youtube.com)
- **Error Categorization** - User-friendly error messages with actionable guidance for common issues
- **Celery Integration** - Asynchronous background processing for downloads
- **Redis Persistence** - Job status and progress tracking with 1-hour TTL
- **Google Cloud Storage (GCS)** - Secure file delivery with signed URLs and automatic cleanup
- **Automatic Cleanup** - GCS lifecycle rules (1-day retention) or Celery beat tasks for local storage

**Celery Download Task:**
- **Async Download Processing** - `download_video` Celery task handles video downloads asynchronously
- **Progress Tracking** - Real-time progress updates via yt-dlp progress hooks with Redis persistence
- **Progress Timeout Handling** - Fallback mechanism for stalled downloads or short videos without progress updates
- **File Storage Integration** - Automatic upload to GCS with fallback to local storage
- **Token Generation** - Secure file tokens with 10-minute expiration for download access
- **Job Completion** - Updates job status with download URL and expiration timestamp
- **Error Handling** - Comprehensive exception handling with error categorization (yt-dlp, OSError, unexpected errors)
- **WebSocket Support** - Optional real-time progress broadcasting via Socket.IO
- **Structured Logging** - Detailed logging with context for debugging and monitoring

**Celery Cleanup Task:**
- **Periodic Cleanup** - `cleanup_expired_jobs` Celery beat task runs every 5 minutes
- **Expired File Cleanup** - Queries Redis for expired file tokens and removes files from local storage or GCS
- **Expired Job Cleanup** - Removes completed/failed jobs older than 1 hour from Redis
- **Orphaned File Cleanup** - Scans `/tmp/ultra-dl/` for orphaned files older than 1 hour
- **GCS Integration** - Deletes expired files from Google Cloud Storage when available
- **Local Storage Cleanup** - Removes expired files from local filesystem as fallback
- **Comprehensive Logging** - Detailed cleanup statistics and error reporting for monitoring
- **Dual Cleanup Strategy** - Application-level cleanup (primary) + GCS lifecycle rules (safety net)

**Safety Features:**
- Rate limiting with Flask-Limiter (Redis-backed) - **only enabled in production** (FLASK_ENV=production)
- Secure token-based file access with HMAC signatures
- GCS signed URLs with 10-minute expiration
- Automatic file cleanup via GCS lifecycle rules
- Progress timeout handling for stalled downloads
- Distributed locking for atomic operations

**Job Management Service:**
- **JobService** - Application service orchestrating job lifecycle operations
  - `create_download_job()` - Creates new download jobs with unique job_id
  - `update_progress()` - Atomically updates job progress with Redis persistence
  - `complete_job()` - Marks jobs as completed with download URL and expiration
  - `fail_job()` - Handles job failures with error categorization
  - `delete_job()` - Removes jobs and associated files
- **JobManager** - Domain service managing job state transitions and validation
- **RedisJobRepository** - Redis-backed persistence with atomic operations
  - Lua scripts for atomic progress and status updates
  - 1-hour TTL for automatic job expiration
  - Distributed locking support for concurrent access
- **Progress Tracking** - Real-time progress updates with percentage, phase, speed, and ETA
  - Atomic Redis operations prevent race conditions
  - Supports polling (default) and WebSocket (optional) delivery

**File Storage Service:**
- **UnifiedFileService** - Coordinates storage and metadata management with automatic GCS/local fallback
  - `register_downloaded_file()` - Saves files to storage and creates metadata with secure tokens
  - `get_file_by_token()` - Retrieves file metadata for download
  - `delete_file()` - Removes files from both storage and metadata
  - `cleanup_expired_files()` - Periodic cleanup of expired files
- **StorageService** - Unified storage abstraction with automatic fallback
  - Detects GCS availability at startup (bucket name, credentials)
  - Automatically falls back to local storage if GCS unavailable
  - `save_file()` - Saves to GCS or local storage with automatic selection
  - `delete_file()` - Removes from appropriate storage backend
- **LocalFileRepository** - Local filesystem storage implementation
  - Stores files in `/tmp/ultra-dl/` organized by job_id
  - Automatic directory creation and cleanup
  - Filename sanitization for security
- **GCSRepository** - Google Cloud Storage integration
  - Uploads files to GCS bucket with proper content types
  - Generates signed URLs with 10-minute expiration
  - Supports GCS lifecycle rules for automatic cleanup
- **SignedUrlService** - Time-limited URL generation
  - Generates cryptographically secure tokens (32 bytes)
  - Creates GCS signed URLs for production
  - Falls back to token-based URLs for local development
  - Optional HMAC signatures for additional security
- **FileManager** - Domain service for file metadata management
  - Token generation and validation
  - Expiration tracking (10-minute TTL)
  - File existence validation
- **RedisFileRepository** - Redis-backed file metadata persistence
  - Stores file tokens with automatic 10-minute TTL
  - Dual mapping: token → file metadata, job_id → token
  - Automatic cleanup of expired entries

**Domain Models:**
- **Job Management** - DownloadJob entity with status transitions (pending, processing, completed, failed)
- **File Storage** - DownloadedFile entity with token-based access and expiration tracking
- **Video Processing** - VideoMetadata and VideoFormat entities for YouTube content representation
- **Value Objects** - JobStatus, JobProgress, YouTubeUrl, FormatType for type safety and validation

**Error Handling:**
- **ErrorCategory Enum** - Structured error categorization (ValidationError, VideoUnavailableError, DownloadError, DownloadTimeout, etc.)
- **categorize_ytdlp_error()** - Maps yt-dlp exceptions to user-friendly error categories
- **ApplicationError** - Base error class with category, technical message, and user-friendly messaging
- **Structured Error Responses** - Consistent error format with code, message, details, and actionable guidance
- **Timeout Handling** - Specific handling for Celery `SoftTimeLimitExceeded` with user-friendly timeout messages

**Design Decisions:**
- Domain-Driven Design (DDD) architecture with clean separation of concerns
- Repository pattern for data access abstraction
- Connection pooling for efficient Redis usage
- Asynchronous job processing for scalability
- GCS integration for secure, scalable file delivery
- Fallback to local file serving when GCS is not available

### Data Flow

1. User enters YouTube URL in frontend
2. Frontend validates URL format client-side
3. Frontend POSTs URL to backend `/api/v1/videos/resolutions` endpoint (port 8000)
4. Backend uses yt-dlp to extract video metadata and available formats
5. Backend returns format list with metadata (title, uploader, thumbnail, formats)
6. Frontend displays video information and available resolutions
7. User selects desired resolution/format
8. Frontend POSTs download request to `/api/v1/downloads/` with URL and format_id
9. Backend creates download job in Redis and enqueues Celery task
10. Backend returns job_id immediately (202 Accepted)
11. Frontend polls `/api/v1/jobs/{job_id}` for progress updates
12. Celery worker downloads video using yt-dlp with progress tracking
13. Worker uploads completed file to GCS (or stores locally as fallback)
14. Worker generates GCS signed URL (or local signed URL) with 10-minute expiration
15. Worker updates job status to "completed" with download URL
16. Frontend receives download URL and displays download button
17. User clicks download button to retrieve file from GCS signed URL
18. GCS automatically deletes files after 1 day via lifecycle rules

### Deployment Configuration

**Docker Services:**
- **Traefik** - Reverse proxy and load balancer (port 80)
- **Redis** - In-memory data store with persistence (port 6379)
- **Backend** - Flask API server (port 8000)
- **Celery Worker** - Background task processor
- **Celery Beat** - Periodic task scheduler
- **Frontend** - React development server (port 5000)

**Development Workflow:**
```bash
# Start all services
docker-compose up

# Start specific service
docker-compose up backend
docker-compose up frontend
docker-compose up redis
docker-compose up celery-worker

# View logs
docker-compose logs -f backend
docker-compose logs -f celery-worker

# Check service health
docker-compose ps
curl http://localhost/health
```

**Port Configuration:**
- Frontend: 5000 (Vite dev server)
- Backend: 8000 (Flask API)
- Redis: 6379
- Traefik: 80 (HTTP)

**Environment Configuration:**
- Copy `.env.example` to `.env` for local development
- Configure Redis, Celery, and rate limiting settings
- Optional GCS configuration for production file storage
- Set `FLASK_ENV=production` to enable rate limiting (disabled by default in development)
- Adjust `CELERY_TASK_SOFT_TIME_LIMIT` (default: 1800s/30min) and `CELERY_TASK_TIME_LIMIT` (default: 2400s/40min) for slow connections

**Integration:**
- Traefik routes requests to appropriate services
- Frontend makes API calls to `http://localhost/api/v1/*`
- Backend connects to Redis for job persistence and rate limiting
- Celery workers process download tasks asynchronously

### External Dependencies

**Frontend Dependencies:**
- **React Router DOM** - Client-side routing
- **TanStack Query** - Server state management and data fetching
- **Radix UI** - Comprehensive set of accessible UI primitives (accordion, dialog, dropdown, etc.)
- **Framer Motion** - Animation library for smooth transitions
- **shadcn/ui** - Pre-built component library built on Radix UI
- **Tailwind CSS** - Utility-first CSS framework
- **Lucide React** - Icon library
- **next-themes** - Theme management (dark/light mode)
- **Sonner** - Toast notifications
- **React Hook Form** - Form state management
- **Zod** - Schema validation (via @hookform/resolvers)

**Backend Dependencies:**
- **Flask** - Web framework for Python
- **flask-cors** - CORS handling for cross-origin requests
- **Flask-Limiter** - Rate limiting with Redis backend
- **yt-dlp** - YouTube video downloader and metadata extractor
- **ffmpeg** (system) - Video/audio processing and merging
- **Celery** - Distributed task queue for async processing
- **Redis** - In-memory data store for job persistence and caching
- **google-cloud-storage** - GCS client library for file uploads and signed URLs

**Development Dependencies:**
- **Vite** - Build tool and dev server
- **TypeScript** - Type system for JavaScript
- **ESLint** - Code linting with TypeScript support
- **PostCSS** - CSS processing with Autoprefixer
- **Lovable Tagger** - Development-only component tagging plugin

**Build Configuration:**
- Development server configured for host 0.0.0.0 on port 5000
- Allowed hosts include localhost and Replit development URLs
- Component tagger enabled only in development mode
- Path aliases for cleaner imports

**External Services:**
- Google Fonts (Inter font family) loaded via CDN
- No database integration currently implemented
- No authentication/authorization services
- No analytics or tracking services mentioned

## Testing

### Backend Integration Tests

The backend includes comprehensive integration tests for all API endpoints, covering:
- Video resolutions endpoint (format extraction and validation)
- Download initiation and job creation
- Job status polling and progress tracking
- File download with token validation
- Job deletion for completed downloads
- Health check endpoint
- Error handling and edge cases
- Rate limiting enforcement

**Running Backend Integration Tests:**
```bash
# Run all integration tests
docker-compose exec backend python test_api_integration.py

# View test output with details
docker-compose exec backend python test_api_integration.py 2>&1 | less
```

**Backend Test Coverage:**
- ✓ Health check endpoint (Requirement 13.1-13.5)
- ✓ Video resolutions with valid/invalid/empty URLs (Requirement 1.1-1.4, 7.1)
- ✓ Complete job lifecycle (create, poll, complete, delete) (Requirement 2.1, 3.1-3.2, 4.1)
- ✓ Download endpoint validation (missing URL/format) (Requirement 2.1, 7.1)
- ✓ Job status for non-existent jobs (Requirement 3.1, 7.1)
- ✓ Delete non-completed job protection (Requirement 12.3)
- ✓ File download with invalid token (Requirement 4.1, 4.5, 7.1)
- ✓ Swagger documentation availability (Requirement 14.1)
- ✓ Swagger JSON schema completeness (Requirement 14.2-14.5)

**Additional Backend Test Scripts:**
- `backend/test_infrastructure.py` - Tests Redis connection, operations, distributed locking, and connection pooling
- `backend/test_job_service.py` - Tests job lifecycle, failure handling, and atomic operations

**Backend Test Requirements:**
- Docker services must be running (redis, backend)
- Tests use the same Redis instance as the application
- Tests are non-destructive and clean up after themselves
- All tests pass with 12/12 success rate

### Frontend Component Tests

The frontend includes component tests using Vitest and React Testing Library, covering:
- UrlInput validation and API integration
- ResolutionPicker format grouping and selection
- ProgressTracker polling and display
- ErrorCard error message rendering

**Running Frontend Component Tests:**
```bash
# Run all component tests
docker-compose exec frontend npx vitest --run

# Run tests in watch mode
docker-compose exec frontend npx vitest

# Run tests with UI
docker-compose exec frontend npx vitest --ui
```

**Frontend Test Coverage:**
- ✓ UrlInput component (7 tests)
  - Input field and button rendering
  - Empty URL validation
  - Invalid YouTube URL format validation
  - Valid YouTube URL acceptance and API calls
  - API error response handling
  - Loading state during API calls
  - Short URL (youtu.be) support
- ✓ ResolutionPicker component (9 tests)
  - Format group rendering (Video+Audio, Video Only, Audio Only)
  - Format grouping by type
  - Format sorting by resolution height
  - Format selection callback
  - Selected resolution highlighting
  - File size display formatting
  - Quality label display
  - Invalid format filtering
  - Null filesize handling
- ✓ ProgressTracker component (12 tests)
  - Pending state rendering
  - Cancel button in pending state
  - Processing state with progress
  - ETA formatting for minutes
  - Completed state with download button
  - Delete button in completed state
  - Failed state with error message
  - Job ID display
  - WebSocket connection status
  - Polling status display
  - Expiration countdown display
  - Missing progress data handling
- ✓ ErrorCard component (9 tests)
  - Error information rendering in alert variant
  - Error information rendering in card variant
  - Retry button display and functionality
  - Retry button hiding when showRetry is false
  - Dismiss button display and functionality
  - Different error category rendering
  - Actionable guidance display
  - Component without buttons
  - Both retry and dismiss buttons together

**Frontend Test Requirements:**
- Docker services must be running (frontend)
- Tests use jsdom environment for DOM simulation
- Tests are isolated and clean up after themselves
- All tests pass with 37/37 success rate

**Test Configuration:**
- Test framework: Vitest with jsdom environment
- Testing utilities: @testing-library/react, @testing-library/jest-dom
- Setup file: `frontend/src/test/setup.ts`
- Configuration: `frontend/vite.config.ts` (test section)

## Infrastructure

### Terraform Configuration

The `terraform/` directory contains Infrastructure as Code (IaC) for deploying the application on Google Cloud Platform (GCP) using the free tier.

**Resources Managed:**
- **GCS Bucket** - Temporary file storage with automatic lifecycle cleanup
- **Compute Engine** - e2-micro instance (free tier eligible)
- **Service Account** - IAM permissions for GCS access
- **Firewall Rules** - HTTP/HTTPS access configuration

**GCS Lifecycle Rules:**
- Automatic deletion of objects after 1 day
- Cleanup of incomplete multipart uploads after 1 day
- Serves as safety net for application-level cleanup

**Documentation:**
- `terraform/README.md` - Complete setup and deployment guide
- `terraform/TESTING.md` - Comprehensive testing instructions for lifecycle rules
- `terraform/LIFECYCLE_RULES.md` - Detailed reference for GCS lifecycle configuration

**Quick Start:**
```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your GCP project details
terraform init
terraform plan
terraform apply
```

For detailed instructions, see [terraform/README.md](terraform/README.md).
