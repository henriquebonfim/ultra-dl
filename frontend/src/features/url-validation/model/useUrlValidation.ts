import { getVideoInfo } from "@/entities/video/api/getVideoInfo";
import type { VideoResolutionsResponse } from "@/entities/video/model/types";
import { formatErrorForToast, parseApiError } from "@/shared/lib/errors";
import { useState } from "react";
import { toast } from "sonner";

export interface ValidationResult {
  isValid: boolean;
  error?: string;
}

export function validateYoutubeUrl(url: string): boolean {
  // Simple regex for YouTube URLs
  const regExp = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+$/;
  return regExp.test(url);
}

export function validateUrlNotEmpty(url: string): boolean {
  return url.trim().length > 0;
}

export function useUrlValidation() {
  const [isValidating, setIsValidating] = useState(false);
  const [isInvalid, setIsInvalid] = useState(false);

  const validateUrl = async (
    url: string
  ): Promise<{ result: ValidationResult; data?: VideoResolutionsResponse }> => {
    // Validate empty URL
    if (!validateUrlNotEmpty(url)) {
      setIsInvalid(true);
      const error = "Please paste a YouTube URL";
      toast.error(error);
      return { result: { isValid: false, error } };
    }

    // Validate URL format
    if (!validateYoutubeUrl(url)) {
      setIsInvalid(true);
      const error = "Invalid YouTube URL";
      toast.error(error);
      return { result: { isValid: false, error } };
    }

    setIsInvalid(false);
    setIsValidating(true);

    try {
      const data = await getVideoInfo(url);

      // Success - show toast
      toast.success("Video found! Select your resolution below.");
      setIsValidating(false);
      return { result: { isValid: true }, data };
    } catch (error) {
      console.error("Error fetching resolutions:", error);
      const errorDetails = parseApiError(error);
      toast.error(formatErrorForToast(errorDetails));
      setIsInvalid(true);
      setIsValidating(false);
      return {
        result: { isValid: false, error: formatErrorForToast(errorDetails) },
      };
    }
  };

  return {
    validateUrl,
    isValidating,
    isInvalid,
    setIsInvalid,
  };
}
