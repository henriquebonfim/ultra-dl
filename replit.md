# UltraDL - YouTube Video Downloader

## Overview

UltraDL is a web-based YouTube video downloader application that allows users to download videos in various resolutions up to 8K. The application consists of a React-based frontend with a Flask/Python backend that leverages yt-dlp for video processing.

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
- Index (/) - Main application page with video download workflow
- NotFound (*) - Catch-all 404 error page

**Component Organization:**
- UI components in src/components/ui/ (shadcn/ui library)
- Feature components in src/components/ (AdBanner, DownloadButton, Footer, Header, ResolutionPicker, UrlInput)
- Hooks in src/hooks/ (use-mobile, use-toast)
- Utility functions in src/lib/utils.ts

### Backend Architecture

**Framework:**
- Single-file Flask application (backend.py)
- Flask-CORS enabled for cross-origin requests from the frontend
- Designed for local development/testing only

**API Endpoints:**
- `/api/resolutions` (POST) - Fetches available video formats/resolutions for a given YouTube URL
- `/api/download` (POST) - Downloads selected video format and streams it to the client
- `/health` (GET) - Health check endpoint for backend status

**Video Processing:**
- yt-dlp library for YouTube metadata extraction and video downloading
- ffmpeg (system dependency) for video/audio merging and processing
- Temporary file handling using tempfile.mkdtemp() for per-request isolation
- Automatic cleanup scheduling with configurable delay (CLEANUP_DELAY_SECONDS)

**Safety Features:**
- Optional file size limits (MAX_RETURN_FILE_SIZE)
- Temporary directory cleanup to prevent disk space issues
- Thread-based cleanup scheduling for downloaded files

**Design Decisions:**
- Single-file backend for simplicity and local development
- Not production-ready (lacks authentication, rate limiting, and security hardening)
- Stateless request handling with ephemeral temporary directories

### Data Flow

1. User enters YouTube URL in frontend
2. Frontend validates URL format client-side
3. Frontend POSTs URL to backend `/api/resolutions` endpoint (port 8000)
4. Backend uses yt-dlp to extract video metadata and available formats
5. Backend returns format list with metadata (title, uploader, thumbnail, formats)
6. Frontend displays video information and available resolutions
7. User selects desired resolution/format
8. Frontend POSTs download request to `/api/download` with URL and format_id
9. Backend downloads video using yt-dlp, merges audio/video if needed
10. Backend streams file as HTTP attachment to frontend
11. Frontend triggers browser download with appropriate filename
12. Backend schedules cleanup of temporary files after delay

### Deployment Configuration

**Workflows:**
- Frontend workflow: `npm run dev` (port 5000) - Vite development server
- Backend workflow: `python3 backend.py` (port 8000) - Flask API server

**Port Configuration:**
- Frontend: 5000 (webview output type)
- Backend: 8000 (console output type)
- Both bound to 0.0.0.0 for Replit compatibility

**Integration:**
- Frontend makes direct fetch calls to `http://localhost:8000/api/*`
- CORS enabled on backend for all origins
- No proxy configuration needed in development

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
- **yt-dlp** - YouTube video downloader and metadata extractor
- **ffmpeg** (system) - Video/audio processing and merging

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