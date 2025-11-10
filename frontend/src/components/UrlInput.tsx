import { useState } from "react";
import { motion } from "framer-motion";
import { Youtube, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { parseApiError, formatErrorForToast } from "@/lib/errors";

interface Resolution {
  format_id: string;
  ext: string;
  resolution: string;
  height: number;
  note: string;
  filesize: number | null;
  vcodec: string;
  acodec: string;
}

interface VideoMeta {
  id: string;
  title: string;
  uploader: string;
  duration: number;
  thumbnail: string;
}

interface VideoResolutionsResponse {
  meta: VideoMeta;
  formats: Resolution[];
}

interface UrlInputProps {
  onSuccess: (data: VideoResolutionsResponse, url: string) => void;
  disabled?: boolean;
}

export const UrlInput = ({ onSuccess, disabled = false }: UrlInputProps) => {
  const [url, setUrl] = useState("");
  const [isInvalid, setIsInvalid] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL;

  const validateYoutubeUrl = (url: string): boolean => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    return youtubeRegex.test(url);
  };

  const handleCheck = async () => {
    // Prevent multiple requests
    if (isLoading || disabled) return;

    // Validate empty URL
    if (!url.trim()) {
      setIsInvalid(true);
      toast.error("Please paste a YouTube URL");
      return;
    }

    // Validate URL format
    if (!validateYoutubeUrl(url)) {
      setIsInvalid(true);
      toast.error("Invalid YouTube URL");
      return;
    }

    setIsInvalid(false);
    setIsLoading(true);

    try {
      // Make API call to fetch video resolutions
      const response = await fetch(`${API_URL}/api/v1/videos/resolutions`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const error = parseApiError(errorData);
        toast.error(formatErrorForToast(error));
        setIsInvalid(true);
        setIsLoading(false);
        return;
      }

      const data: VideoResolutionsResponse = await response.json();
      
      // Success - show toast and call success callback
      toast.success("Video found! Select your resolution below.");
      onSuccess(data, url);
      setIsLoading(false);
    } catch (error) {
      console.error("Error fetching resolutions:", error);
      const errorDetails = parseApiError(error);
      toast.error(formatErrorForToast(errorDetails));
      setIsInvalid(true);
      setIsLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="w-full max-w-3xl mx-auto space-y-4"
    >
      <div className="bg-card shadow-card rounded-2xl p-6 md:p-8 border border-border">
        <div className="flex flex-col gap-4">
          <div className="relative">
            <Youtube className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Paste your YouTube link here..."
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setIsInvalid(false);
              }}
              onKeyDown={(e) => e.key === "Enter" && !disabled && !isLoading && handleCheck()}
              disabled={disabled || isLoading}
              className={`pl-12 pr-4 py-6 text-base bg-input border-2 transition-all duration-300 ${
                isInvalid
                  ? "border-destructive focus-visible:ring-destructive"
                  : "border-border focus-visible:ring-primary"
              }`}
              data-testid="input-youtube-url"
            />
          </div>
          <Button
            onClick={handleCheck}
            disabled={disabled || isLoading}
            className="w-full py-6 text-base font-semibold gradient-primary shadow-glow hover:opacity-90 transition-opacity disabled:opacity-50"
            size="lg"
            data-testid="button-check-video"
          >
            <Search className="mr-2 h-5 w-5" />
            {isLoading ? "Checking..." : "Check Video"}
          </Button>
        </div>
      </div>
    </motion.div>
  );
};
