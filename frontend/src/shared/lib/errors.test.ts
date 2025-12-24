import { describe, expect, it } from 'bun:test';
import {
  ERROR_MESSAGES,
  ErrorCategory,
  ErrorInfo,
  formatErrorForToast,
  getErrorInfo,
  isRetryableError,
  parseApiError,
} from './errors';

describe('Error Handling Utilities', () => {
  describe('parseApiError', () => {
    it('should return correct error info for known error category in error object', () => {
      const apiError = { error: ErrorCategory.INVALID_URL };
      const result = parseApiError(apiError);
      expect(result).toEqual(ERROR_MESSAGES[ErrorCategory.INVALID_URL]);
    });

    it('should return structured error info if provided in error object', () => {
      const customError: ErrorInfo = {
        title: 'Custom Error',
        message: 'Something went wrong',
        action: 'Retry',
      };
      const apiError = { ...customError, error: 'some_unknown_category' };
      const result = parseApiError(apiError);
      expect(result).toEqual(customError);
    });

    it('should return NETWORK_ERROR for fetch TypeErrors', () => {
      const fetchError = new TypeError('Failed to fetch');
      const result = parseApiError(fetchError);
      expect(result).toEqual(ERROR_MESSAGES[ErrorCategory.NETWORK_ERROR]);
    });

    it('should return SYSTEM_ERROR for unknown errors', () => {
      const unknownError = new Error('Random error');
      const result = parseApiError(unknownError);
      expect(result).toEqual(ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR]);
    });

    it('should return SYSTEM_ERROR for null/undefined', () => {
      expect(parseApiError(null)).toEqual(ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR]);
      expect(parseApiError(undefined)).toEqual(ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR]);
    });
  });

  describe('getErrorInfo', () => {
    it('should return correct error info for valid category', () => {
      const result = getErrorInfo(ErrorCategory.RATE_LIMITED);
      expect(result).toEqual(ERROR_MESSAGES[ErrorCategory.RATE_LIMITED]);
    });

    it('should return SYSTEM_ERROR for invalid category', () => {
      // @ts-ignore - testing runtime safety
      const result = getErrorInfo('invalid_category');
      expect(result).toEqual(ERROR_MESSAGES[ErrorCategory.SYSTEM_ERROR]);
    });
  });

  describe('formatErrorForToast', () => {
    it('should format error info correctly', () => {
      const info: ErrorInfo = {
        title: 'Error Title',
        message: 'Error Message',
        action: 'Do something',
      };
      expect(formatErrorForToast(info)).toBe('Error Title: Error Message');
    });
  });

  describe('isRetryableError', () => {
    it('should identify retryable errors', () => {
      expect(isRetryableError(ErrorCategory.NETWORK_ERROR)).toBe(true);
      expect(isRetryableError(ErrorCategory.DOWNLOAD_FAILED)).toBe(true);
      expect(isRetryableError(ErrorCategory.SYSTEM_ERROR)).toBe(true);
      expect(isRetryableError(ErrorCategory.PLATFORM_RATE_LIMITED)).toBe(true);
    });

    it('should identify non-retryable errors', () => {
      expect(isRetryableError(ErrorCategory.INVALID_URL)).toBe(false);
      expect(isRetryableError(ErrorCategory.VIDEO_UNAVAILABLE)).toBe(false);
    });
  });
});
