import { useToast } from "@/shared/hooks/use-toast";
import { Button } from "@/shared/ui/button";
import { Progress } from "@/shared/ui/progress";
import { Clock, Download, Loader2 } from "lucide-react";

interface DownloadProgressProps {
  progress: number;
  fileName: string;
  estimatedTime?: string;
  downloadUrl?: string;
  isProcessing?: boolean;
  phase?: string;
}

export const DownloadProgress = ({
  progress,
  fileName,
  estimatedTime,
  downloadUrl,
  isProcessing,
  phase,
}: DownloadProgressProps) => {
  const { toast } = useToast();
  const isComplete = progress >= 100;

  const handleDownload = () => {
    if (downloadUrl) {
      const link = document.createElement("a");
      link.href = downloadUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast({
        title: "Download started!",
        description: `Downloading ${fileName}`,
      });
    }
  };

  // Helper to determine status text based on phase
  const getStatusText = () => {
    if (isComplete) return "Complete!";

    if (phase) {
      switch (phase.toLowerCase()) {
        case "converting":
          return "Converting format...";
        case "trimming":
          return "Trimming video...";
        case "merging":
          return "Merging audio/video...";
        case "processing":
          return "Processing...";
        case "downloading":
          return "Downloading...";
        case "extracting metadata":
          return "Preparing...";
        default:
          return "Processing...";
      }
    }

    return isProcessing ? "Processing..." : "Downloading...";
  };

  return (
    <div className="w-full space-y-4 p-6 bg-card rounded-xl border border-border">
      {/* File Name */}
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-foreground truncate max-w-[70%]">{fileName}</h3>
        {estimatedTime && !isComplete && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>{estimatedTime}</span>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="space-y-2">
        <div className="relative">
          <Progress
            value={progress}
            className="h-3 bg-secondary"
            aria-label={`Download progress: ${progress}%`}
          />
          {isProcessing && progress < 100 && (
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-primary/20 to-transparent animate-shimmer" />
          )}
        </div>
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {getStatusText()}
          </span>
          <span className="font-medium text-primary">{Math.round(progress)}%</span>
        </div>
      </div>

      {/* Action Buttons */}
      {isComplete && downloadUrl && (
        <div className="flex flex-wrap gap-3 pt-2">
          <Button
            onClick={handleDownload}
            className="flex-1 bg-gradient-primary hover:opacity-90 transition-opacity"
            aria-label={`Download ${fileName}`}
          >
            <Download className="mr-2 h-4 w-4" />
            Save File
          </Button>

        </div>
      )}

      {isProcessing && !isComplete && (
        <div className="flex items-center justify-center gap-2 text-muted-foreground pt-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span className="text-sm">Please wait while we process your video...</span>
        </div>
      )}
    </div>
  );
};
