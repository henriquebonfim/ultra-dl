import { ProgressTracker } from "@/components/ProgressTracker";
import { Button } from "@/components/ui/button";
import { useJobStatusWithWebSocket } from "@/hooks/useJobStatusWithWebSocket";
import { AnimatePresence, motion } from "framer-motion";
import { Download } from "lucide-react";
import { useState } from "react";
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

interface DownloadButtonProps {
  disabled: boolean;
  onCreateJob: () => Promise<string | null>;
  selectedResolution: Resolution | null;
  videoMeta: VideoMeta | null;
  onJobCancel?: () => void;
}

export const DownloadButton = ({ disabled, onCreateJob, selectedResolution, videoMeta, onJobCancel }: DownloadButtonProps) => {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isCreatingJob, setIsCreatingJob] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL;

  // Use enhanced hook with WebSocket support and automatic polling fallback
  const {
    data: jobStatus,
    error: jobError,
    connectionMethod,
    isWebSocketConnected,
    disconnect
  } = useJobStatusWithWebSocket(jobId, {
    enabled: !!jobId,
    preferWebSocket: true
  });

  const handleCreateJob = async () => {
    // Prevent multiple requests
    if (isCreatingJob || jobId) return;
    
    setIsCreatingJob(true);
    try {
      const newJobId = await onCreateJob();
      if (newJobId) {
        setJobId(newJobId);
      }
    } finally {
      setIsCreatingJob(false);
    }
  };

  const handleDownloadFile = () => {
    if (jobStatus?.download_url) {
      try {
        // Open download in new tab
        window.open(jobStatus.download_url, "_blank");

        // Show success message
        toast.success("Download started!", {
          description: "Your video download has begun.",
        });
      } catch (error) {
        // Handle expired URL or other errors
        const errorInfo = parseApiError(error);
        toast.error(formatErrorForToast(errorInfo));
      }
    }
  };

  const handleExpire = () => {
    // Disconnect WebSocket when download expires
    disconnect();

    // Show expiration alert with more prominent styling
    toast.error("💥 Download Expired!", {
      description: "Your download link has expired and the file has been deleted to free up storage space. Please start a new download if needed.",
      duration: 10000, // Show for 10 seconds
    });

    // Clear job after a delay to allow animation to complete
    setTimeout(() => {
      setJobId(null);
      if (onJobCancel) {
        onJobCancel();
      }
    }, 2500);
  };

  const handleDeleteJob = async () => {
    if (!jobId || !jobStatus) return;

    const isCompleted = jobStatus.status === "completed" || jobStatus.status === "failed";
    const action = isCompleted ? "deleted" : "cancelled";

    try {
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}`, {
        method: "DELETE",
      });

      if (response.ok) {
        // Show success message based on job status
        if (isCompleted) {
          toast.success("Job deleted!", {
            description: "The job and its file have been removed.",
          });
        } else {
          toast.success("Download cancelled!", {
            description: "The download has been stopped and resources cleaned up.",
          });
        }

        // Reset job state
        setJobId(null);
        
        // Call parent callback to reset download state
        if (onJobCancel) {
          onJobCancel();
        }
      } else {
        const errorData = await response.json();
        const errorInfo = parseApiError(errorData);
        toast.error(formatErrorForToast(errorInfo));
      }
    } catch (error) {
      const errorInfo = parseApiError(error);
      toast.error(formatErrorForToast(errorInfo));
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.4 }}
      className="w-full max-w-2xl mx-auto"
    >
      <AnimatePresence mode="wait">
        {!jobId && (
          <motion.div
            key="download-button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Button
              onClick={handleCreateJob}
              disabled={disabled || isCreatingJob}
              className="w-full py-6 text-lg font-semibold gradient-primary shadow-glow hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              size="lg"
              data-testid="button-download"
            >
              <Download className="mr-2 h-6 w-6" />
              {isCreatingJob ? "Starting Download..." : `Download ${selectedResolution?.resolution || "Video"}`}
            </Button>
            {selectedResolution && videoMeta && (
              <p className="text-center text-sm text-muted-foreground mt-3" data-testid="text-download-info">
                Ready to download: {videoMeta.title} ({selectedResolution.resolution})
              </p>
            )}
          </motion.div>
        )}

        {jobId && jobStatus && (
          <motion.div
            key="progress-tracker"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
          >
            <ProgressTracker
              jobId={jobId}
              status={jobStatus.status}
              progress={jobStatus.progress}
              downloadUrl={jobStatus.download_url}
              error={jobError?.message || jobStatus.error}
              onDownload={handleDownloadFile}
              onDelete={handleDeleteJob}
              onExpire={handleExpire}
              connectionMethod={connectionMethod}
              isWebSocketConnected={isWebSocketConnected}
              expireAt={jobStatus.expire_at}
              timeRemaining={jobStatus.time_remaining}
              videoMetadata={videoMeta && selectedResolution ? {
                title: videoMeta.title,
                uploader: videoMeta.uploader,
                duration: videoMeta.duration,
                resolution: selectedResolution.resolution,
                ext: selectedResolution.ext,
                filesize: selectedResolution.filesize,
              } : undefined}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
