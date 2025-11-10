import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { motion } from "framer-motion";
import { CheckCircle2, Download, Loader2, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { parseApiError } from "@/lib/errors";
import { ErrorCard } from "@/components/ErrorCard";

interface JobProgress {
  percentage: number;
  phase: string;
  speed?: string;
  eta?: number;
}

interface VideoMetadata {
  title: string;
  uploader: string;
  duration: number;
  resolution: string;
  ext: string;
  filesize?: number | null;
}

interface ProgressTrackerProps {
  jobId: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: JobProgress | null;
  downloadUrl?: string;
  error?: string;
  onDownload?: () => void;
  onDelete?: () => void;
  onExpire?: () => void;
  connectionMethod?: "websocket" | "polling" | "none";
  isWebSocketConnected?: boolean;
  expireAt?: string;
  timeRemaining?: number;
  videoMetadata?: VideoMetadata;
}

const formatETA = (seconds: number | undefined): string => {
  if (!seconds) return "Calculating...";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
};

const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  
  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
};

const formatFilesize = (bytes: number | null | undefined): string => {
  if (!bytes) return "Unknown size";
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) {
    return `${mb.toFixed(2)} MB`;
  }
  const gb = mb / 1024;
  return `${gb.toFixed(2)} GB`;
};

export const ProgressTracker = ({
  jobId,
  status,
  progress,
  downloadUrl,
  error,
  onDownload,
  onDelete,
  onExpire,
  connectionMethod = "none",
  isWebSocketConnected = false,
  expireAt,
  timeRemaining: initialTimeRemaining,
  videoMetadata,
}: ProgressTrackerProps) => {
  const [timeRemaining, setTimeRemaining] = useState<string>("");
  const [hasExpired, setHasExpired] = useState(false);
  const [isExploding, setIsExploding] = useState(false);
  const [shouldHide, setShouldHide] = useState(false);

  // Countdown timer using time_remaining from API
  useEffect(() => {
    if (status !== "completed" || initialTimeRemaining === undefined) {
      return;
    }

    let secondsLeft = initialTimeRemaining;

    const updateDisplay = () => {
      if (secondsLeft <= 0) {
        setTimeRemaining("Expired");
        if (!hasExpired) {
          setHasExpired(true);
          setIsExploding(true);
          
          // Hide card after explosion animation (2 seconds)
          setTimeout(() => {
            setShouldHide(true);
          }, 2000);
          
          onExpire?.();
        }
        return;
      }

      const hours = Math.floor(secondsLeft / 3600);
      const minutes = Math.floor((secondsLeft % 3600) / 60);
      const seconds = secondsLeft % 60;

      if (hours > 0) {
        setTimeRemaining(`${hours}h ${minutes}m`);
      } else if (minutes > 0) {
        setTimeRemaining(`${minutes}m ${seconds}s`);
      } else {
        setTimeRemaining(`${seconds}s`);
      }
    };

    const tick = () => {
      secondsLeft--;
      updateDisplay();
    };

    // Initial display
    updateDisplay();

    // Update every second
    const interval = setInterval(tick, 1000);

    return () => clearInterval(interval);
  }, [initialTimeRemaining, status, hasExpired, onExpire]);

  // Don't render if hidden after explosion
  if (shouldHide) {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={
        isExploding
          ? {
              scale: [1, 1.1, 0.9, 1.2, 0],
              opacity: [1, 0.8, 0.6, 0.3, 0],
              rotate: [0, -5, 5, -10, 0],
              filter: [
                "blur(0px)",
                "blur(2px)",
                "blur(4px)",
                "blur(8px)",
                "blur(20px)",
              ],
            }
          : { opacity: 1, scale: 1 }
      }
      exit={{ opacity: 0, scale: 0.95 }}
      transition={
        isExploding
          ? {
              duration: 2,
              ease: "easeInOut",
              times: [0, 0.2, 0.5, 0.8, 1],
            }
          : { duration: 0.3 }
      }
      className="w-full max-w-2xl mx-auto bg-card rounded-2xl p-6 border border-border shadow-card"
      data-testid="progress-tracker"
    >
      {/* Pending State */}
      {status === "pending" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
              <div>
                <h3 className="font-semibold">Preparing download...</h3>
                <p className="text-sm text-muted-foreground">Your download will start shortly</p>
              </div>
            </div>
            {onDelete && (
              <Button
                onClick={onDelete}
                variant="outline"
                className="border-red-300 text-red-600 hover:bg-red-50 hover:border-red-400"
                size="sm"
                data-testid="button-cancel-job"
              >
                Cancel
              </Button>
            )}
          </div>
        </div>
      )}

      {/* Processing State */}
      {status === "processing" && progress && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
              <div>
                <h3 className="font-semibold">Downloading your video</h3>
                <p className="text-sm text-muted-foreground capitalize">{progress.phase}</p>
              </div>
            </div>
            <span className="text-2xl font-bold text-primary">{progress.percentage}%</span>
          </div>

          <Progress value={progress.percentage} className="h-3" />

          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{progress.speed || "Calculating speed..."}</span>
            <span>ETA: {formatETA(progress.eta)}</span>
          </div>

          {onDelete && (
            <div className="flex justify-center mt-4">
              <Button
                onClick={onDelete}
                variant="outline"
                className="border-red-300 text-red-600 hover:bg-red-50 hover:border-red-400"
                size="sm"
                data-testid="button-cancel-download"
              >
                <Trash2 className="mr-2 h-4 w-4" />
                Cancel Download
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Completed State */}
      {status === "completed" && (
        <div className="space-y-4">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 className="h-6 w-6 text-green-500" />
            <div>
              <h3 className="font-semibold text-green-500">Download ready!</h3>
              <p className="text-sm text-muted-foreground">Your video is ready to download</p>
            </div>
          </div>

          {downloadUrl && (
            <div className="flex gap-3">
              <Button
                onClick={onDownload}
                className="flex-1 py-6 text-lg font-bold gradient-primary shadow-glow hover:opacity-90 transition-opacity"
                size="lg"
                data-testid="button-download-file"
              >
                <Download className="mr-2 h-6 w-6" />
                Download Video
              </Button>
              {onDelete && (
                <Button
                  onClick={onDelete}
                  variant="outline"
                  className="px-4 py-6 border-none text-red-600 hover:bg-red-50 hover:border-red-300"
                  size="lg"
                  data-testid="button-delete-job"
                >
                  <Trash2 className="h-5 w-5" />
                </Button>
              )}
            </div>
          )}

          {/* Video Metadata */}
          {videoMetadata && (
            <div className="mt-4 p-4 bg-muted/50 rounded-lg border border-border">
              <h4 className="text-sm font-semibold mb-3 text-foreground">Video Information</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Title:</span>
                  <span className="font-medium text-foreground text-right ml-4 max-w-[60%] truncate" title={videoMetadata.title}>
                    {videoMetadata.title}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Channel:</span>
                  <span className="font-medium text-foreground">{videoMetadata.uploader}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Duration:</span>
                  <span className="font-medium text-foreground">{formatDuration(videoMetadata.duration)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Resolution:</span>
                  <span className="font-medium text-foreground">{videoMetadata.resolution}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Format:</span>
                  <span className="font-medium text-foreground uppercase">{videoMetadata.ext}</span>
                </div>
                {videoMetadata.filesize && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">File Size:</span>
                    <span className="font-medium text-foreground">{formatFilesize(videoMetadata.filesize)}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Expiration Countdown */}
          {expireAt && (
            <div className="mt-4 text-center space-y-1">
              <span className="text-sm text-muted-foreground">
                Expires in: <span className="font-semibold text-primary">{timeRemaining}</span>
              </span>
              <p className="text-xs text-muted-foreground">
                Files are automatically deleted after expiration to free up storage space.
              </p>
            </div>
          )}
        </div>
      )}

      {/* Failed State */}
      {status === "failed" && (
        <div className="space-y-4">
          <ErrorCard
            error={parseApiError({ error: error || "An unexpected error occurred. Please try again." })}
            onRetry={onDelete}
            variant="card"
            showRetry={!!onDelete}
          />
        </div>
      )}

      {/* Job ID and connection method for debugging */}
      <div className="text-xs text-muted-foreground mt-4 text-center space-y-1">
        <p>Job ID: {jobId}</p>
        {status === "completed" && expireAt ? (
          <p className="flex items-center justify-center gap-1">
            <span className="inline-block w-2 h-2 rounded-full bg-blue-500" />
            Expires in: {timeRemaining}
          </p>
        ) : connectionMethod !== "none" ? (
          <p className="flex items-center justify-center gap-1">
            <span className={`inline-block w-2 h-2 rounded-full ${
              connectionMethod === "websocket" && isWebSocketConnected
                ? "bg-green-500 animate-pulse"
                : "bg-yellow-500"
            }`} />
            {connectionMethod === "websocket" && isWebSocketConnected
              ? "Real-time updates"
              : "Polling updates"}
          </p>
        ) : null}
      </div>
    </motion.div>
  );
};
