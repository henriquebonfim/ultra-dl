# Error Handling System Documentation

## Overview

The error handling system provides a consistent, user-friendly way to display and manage errors throughout the application. It maps backend error categories to actionable user guidance and supports multiple display formats.

## Components

### ErrorCard

A comprehensive error display component with title, message, and actionable guidance.

**Props:**
- `error: ErrorInfo` - Error information object
- `onRetry?: () => void` - Optional retry callback
- `onDismiss?: () => void` - Optional dismiss callback
- `variant?: "alert" | "card"` - Display variant (default: "alert")
- `showRetry?: boolean` - Show retry button (default: true)

**Usage:**
```tsx
import { ErrorCard } from "@/components/ErrorCard";
import { parseApiError } from "@/lib/errors";

function MyComponent() {
  const [error, setError] = useState(null);

  const handleApiCall = async () => {
    try {
      const response = await fetch("/api/endpoint");
      if (!response.ok) {
        const errorData = await response.json();
        setError(parseApiError(errorData));
      }
    } catch (err) {
      setError(parseApiError(err));
    }
  };

  return (
    <>
      {error && (
        <ErrorCard
          error={error}
          onRetry={handleApiCall}
          onDismiss={() => setError(null)}
          variant="alert"
        />
      )}
    </>
  );
}
```

### ErrorMessage

Simple inline error message for form validation and quick feedback.

**Props:**
- `message: string` - Error message text
- `className?: string` - Optional CSS classes

**Usage:**
```tsx
import { ErrorMessage } from "@/components/ErrorMessage";

function FormField() {
  const [error, setError] = useState("");

  return (
    <>
      <input onChange={(e) => validate(e.target.value)} />
      {error && <ErrorMessage message={error} />}
    </>
  );
}
```

## Utilities

### Error Categories

All supported error categories from `ErrorCategory` enum:

- `INVALID_URL` - YouTube URL validation errors
- `VIDEO_UNAVAILABLE` - Private, deleted, or restricted videos
- `FORMAT_NOT_SUPPORTED` - Unavailable format selections
- `DOWNLOAD_FAILED` - General download errors
- `FILE_TOO_LARGE` - Size limit exceeded
- `RATE_LIMITED` - Too many requests
- `SYSTEM_ERROR` - Unexpected errors
- `JOB_NOT_FOUND` - Missing or expired jobs
- `INVALID_REQUEST` - Malformed requests
- `NETWORK_ERROR` - Connection issues
- `FILE_NOT_FOUND` - Missing files
- `FILE_EXPIRED` - Expired download links
- `GEO_BLOCKED` - Region-restricted content
- `LOGIN_REQUIRED` - Authentication needed
- `PLATFORM_RATE_LIMITED` - YouTube rate limiting

### parseApiError()

Parses API error responses and returns structured error information.

**Usage:**
```tsx
import { parseApiError } from "@/lib/errors";

try {
  const response = await fetch("/api/endpoint");
  if (!response.ok) {
    const errorData = await response.json();
    const errorInfo = parseApiError(errorData);
    // errorInfo contains: { title, message, action }
  }
} catch (error) {
  const errorInfo = parseApiError(error);
}
```

### formatErrorForToast()

Formats error information for toast notifications (shorter message).

**Usage:**
```tsx
import { formatErrorForToast, parseApiError } from "@/lib/errors";
import { toast } from "sonner";

const errorInfo = parseApiError(error);
toast.error(formatErrorForToast(errorInfo));
```

### getErrorInfo()

Gets error information from error category.

**Usage:**
```tsx
import { getErrorInfo, ErrorCategory } from "@/lib/errors";

const errorInfo = getErrorInfo(ErrorCategory.VIDEO_UNAVAILABLE);
// Returns: { title, message, action }
```

### isRetryableError()

Determines if an error can be retried.

**Usage:**
```tsx
import { isRetryableError, ErrorCategory } from "@/lib/errors";

const canRetry = isRetryableError(ErrorCategory.NETWORK_ERROR); // true
const canRetry2 = isRetryableError(ErrorCategory.INVALID_URL); // false
```

## Hooks

### useApiError

Custom hook for consistent error handling with state management.

**Returns:**
- `error: ErrorInfo | null` - Current error state
- `handleError: (err: unknown, showToast?: boolean) => ErrorInfo` - Error handler
- `clearError: () => void` - Clear error state

**Usage:**
```tsx
import { useApiError } from "@/hooks/useApiError";

function MyComponent() {
  const { error, handleError, clearError } = useApiError();

  const fetchData = async () => {
    try {
      const response = await fetch("/api/endpoint");
      if (!response.ok) {
        const errorData = await response.json();
        handleError(errorData); // Automatically shows toast
      }
    } catch (err) {
      handleError(err, false); // Don't show toast
    }
  };

  return (
    <>
      {error && (
        <ErrorCard
          error={error}
          onRetry={fetchData}
          onDismiss={clearError}
        />
      )}
    </>
  );
}
```

## Integration with Backend

The error handling system is designed to work seamlessly with the backend error responses:

**Backend Error Response Format:**
```json
{
  "error": "video_unavailable",
  "title": "Video Not Available",
  "message": "This video cannot be downloaded. It may be private, deleted, or restricted.",
  "action": "Try a different video or check if the video is publicly available."
}
```

The `parseApiError()` function automatically extracts this information and maps it to the frontend error structure.

## Best Practices

1. **Always use parseApiError()** when handling API errors to ensure consistent error formatting
2. **Show toast notifications** for transient errors (network, rate limiting)
3. **Use ErrorCard** for detailed error display with retry/dismiss actions
4. **Use ErrorMessage** for inline form validation
5. **Check isRetryableError()** before showing retry buttons
6. **Clear errors** when user takes action (e.g., typing in input field)
7. **Provide context** in error messages about what went wrong and how to fix it

## Examples

See `frontend/src/examples/ErrorHandlingExample.tsx` for comprehensive examples of all error handling patterns.

## Testing

To test the error handling system:

1. Start the development server: `docker-compose up`
2. Navigate to the application
3. Try various error scenarios:
   - Invalid YouTube URL
   - Private/deleted video
   - Network disconnection
   - Rate limiting (make many requests quickly)
4. Verify error messages are clear and actionable
5. Test retry and dismiss functionality

## Future Enhancements

- Error tracking/logging integration (Sentry, LogRocket)
- Error recovery strategies (automatic retry with exponential backoff)
- Offline error handling
- Error boundary components for React error catching
- Localization support for error messages
