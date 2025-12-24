/**
 * Error Handling Utilities
 *
 * Maps backend error categories to user-friendly messages with actionable guidance.
 * Provides consistent error handling across the application.
 */

export enum ErrorCategory {
  INVALID_URL = "invalid_url",
  VIDEO_UNAVAILABLE = "video_unavailable",
  FORMAT_NOT_SUPPORTED = "format_not_supported",
  DOWNLOAD_FAILED = "download_failed",
  FILE_TOO_LARGE = "file_too_large",
  RATE_LIMITED = "rate_limited",
  SYSTEM_ERROR = "system_error",
  JOB_NOT_FOUND = "job_not_found",
  INVALID_REQUEST = "invalid_request",
  NETWORK_ERROR = "network_error",
  FILE_NOT_FOUND = "file_not_found",
  FILE_EXPIRED = "file_expired",
  GEO_BLOCKED = "geo_blocked",
  LOGIN_REQUIRED = "login_required",
  PLATFORM_RATE_LIMITED = "platform_rate_limited",
}

export interface ErrorInfo {
  title: string;
  message: string;
  action: string;
}

export interface ApiErrorResponse {
  error?: string;
  title?: string;
  message?: string;
  action?: string;
}

/**
 * User-friendly error messages with actionable guidance
 */
export const ERROR_MESSAGES: Record<ErrorCategory, ErrorInfo> = {
  [ErrorCategory.INVALID_URL]: {
    title: "Invalid YouTube URL",
    message: "Please check the URL and make sure it's a valid YouTube link.",
    action: "Try copying the URL directly from YouTube.",
  },
  [ErrorCategory.VIDEO_UNAVAILABLE]: {
    title: "Video Not Available",
    message: "This video cannot be downloaded. It may be private, deleted, or restricted.",
    action: "Try a different video or check if the video is publicly available.",
  },
  [ErrorCategory.FORMAT_NOT_SUPPORTED]: {
    title: "Format Not Supported",
    message: "The selected video format is not available for download.",
    action: "Please choose a different quality or format option.",
  },
  [ErrorCategory.DOWNLOAD_FAILED]: {
    title: "Download Failed",
    message: "The download could not be completed due to an error.",
    action: "Please try again. If the problem persists, try a different format.",
  },
  [ErrorCategory.FILE_TOO_LARGE]: {
    title: "File Too Large",
    message: "The selected video file exceeds the maximum allowed size.",
    action: "Try selecting a lower quality format to reduce file size.",
  },
  [ErrorCategory.RATE_LIMITED]: {
    title: "Too Many Requests",
    message: "You've made too many requests in a short time.",
    action: "Please wait a moment before trying again.",
  },
  [ErrorCategory.SYSTEM_ERROR]: {
    title: "System Error",
    message: "An unexpected error occurred while processing your request.",
    action: "Please try again later. If the problem persists, contact support.",
  },
  [ErrorCategory.JOB_NOT_FOUND]: {
    title: "Job Not Found",
    message: "The requested download job could not be found or has expired.",
    action: "Please start a new download.",
  },
  [ErrorCategory.INVALID_REQUEST]: {
    title: "Invalid Request",
    message: "The request is missing required information or contains invalid data.",
    action: "Please check your input and try again.",
  },
  [ErrorCategory.NETWORK_ERROR]: {
    title: "Network Error",
    message: "Unable to connect to YouTube or download the video.",
    action: "Check your internet connection and try again.",
  },
  [ErrorCategory.FILE_NOT_FOUND]: {
    title: "File Not Found",
    message: "The requested file could not be found or has been deleted.",
    action: "Please download the video again.",
  },
  [ErrorCategory.FILE_EXPIRED]: {
    title: "File Expired",
    message: "The download link has expired. Files are available for 10 minutes after download.",
    action: "Please download the video again to get a new link.",
  },
  [ErrorCategory.GEO_BLOCKED]: {
    title: "Content Not Available in Your Region",
    message: "This video is not available for download in your current location due to geographic restrictions.",
    action: "Try using a VPN or check if the video is available in your region on YouTube directly.",
  },
  [ErrorCategory.LOGIN_REQUIRED]: {
    title: "Login Required",
    message: "This video requires you to be logged in to YouTube to access it.",
    action: "This type of content cannot be downloaded automatically. Please watch it directly on YouTube.",
  },
  [ErrorCategory.PLATFORM_RATE_LIMITED]: {
    title: "Platform Rate Limited",
    message: "YouTube is temporarily limiting download requests. This is normal and helps prevent abuse.",
    action: "Please wait a few minutes before trying again. Avoid making too many requests in a short time.",
  },
};

/**
 * Parse API error response and return structured error information
 */
export function parseApiError(error: unknown): ErrorInfo {
  // Handle API error responses
  if (error && typeof error === "object" && "error" in error) {
    const apiError = error as ApiErrorResponse;

    // If backend provides structured error with title, message, action
    if (apiError.title && apiError.message && apiError.action) {
      return {
        title: apiError.title,
        message: apiError.message,
        action: apiError.action,
      };
    }

    // If backend provides error category
    if (apiError.error && Object.values(ErrorCategory).includes(apiError.error as ErrorCategory)) {
      const category = apiError.error as ErrorCategory;
      return ERROR_MESSAGES[category];
    }
  }

  // Handle network errors
  if (error instanceof TypeError && error.message.includes("fetch")) {
    return ERROR_MESSAGES[ErrorCategory.NETWORK_ERROR];
  }

  // Default to system error
  return ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR];
}

/**
 * Get error info from error category
 */
export function getErrorInfo(category: ErrorCategory): ErrorInfo {
  return ERROR_MESSAGES[category] || ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR];
}

/**
 * Format error for toast notification (shorter message)
 */
export function formatErrorForToast(errorInfo: ErrorInfo): string {
  return `${errorInfo.title}: ${errorInfo.message}`;
}

/**
 * Check if error is retryable
 */
export function isRetryableError(category: ErrorCategory): boolean {
  const retryableErrors = [
    ErrorCategory.NETWORK_ERROR,
    ErrorCategory.DOWNLOAD_FAILED,
    ErrorCategory.SYSTEM_ERROR,
    ErrorCategory.PLATFORM_RATE_LIMITED,
  ];
  return retryableErrors.includes(category);
}
