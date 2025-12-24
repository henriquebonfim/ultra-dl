import { deleteJob } from "@/entities/job/api/deleteJob";
import { formatErrorForToast, parseApiError } from "@/shared/lib/errors";
import { useState } from "react";
import { toast } from "sonner";

export function useDownload() {
  const [isCreatingJob, setIsCreatingJob] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);

  const createJob = async (onCreateJob: () => Promise<string | null>) => {
    // Prevent multiple requests
    if (isCreatingJob || jobId) return null;

    setIsCreatingJob(true);
    try {
      const newJobId = await onCreateJob();
      if (newJobId) {
        setJobId(newJobId);
      }
      return newJobId;
    } catch (error) {
      // Errors should be handled by the caller or inside onCreateJob,
      // but we catch here to reset loading state
      const errorInfo = parseApiError(error);
      toast.error(formatErrorForToast(errorInfo));
      return null;
    } finally {
      setIsCreatingJob(false);
    }
  };

  const deleteCurrentJob = async (currentJobId: string, onJobCancel?: () => void) => {
    if (!currentJobId) return;

    try {
      await deleteJob(currentJobId);

      toast.success("Job deleted!", {
        description: "The job and its file have been removed.",
      });

      // Reset job state
      setJobId(null);

      // Call parent callback to reset download state
      if (onJobCancel) {
        onJobCancel();
      }
    } catch (error) {
      const errorInfo = parseApiError(error);
      toast.error(formatErrorForToast(errorInfo));
    }
  };

  const handleDownloadFile = (downloadUrl?: string) => {
    if (downloadUrl) {
      try {
        // Open download in new tab
        window.open(downloadUrl, "_blank");

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

  const handleExpire = (onJobCancel?: () => void, disconnect?: () => void) => {
    // Disconnect WebSocket when download expires
    if (disconnect) {
      disconnect();
    }

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

  const resetJob = () => {
    setJobId(null);
  };

  return {
    isCreatingJob,
    jobId,
    createJob,
    deleteJob: deleteCurrentJob,
    handleDownloadFile,
    handleExpire,
    resetJob,
  };
}
