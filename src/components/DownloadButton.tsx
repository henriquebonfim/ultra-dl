import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface DownloadButtonProps {
  disabled: boolean;
  onDownload: () => void;
}

export const DownloadButton = ({ disabled, onDownload }: DownloadButtonProps) => {
  const [isDownloading, setIsDownloading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleDownload = () => {
    setIsDownloading(true);
    setProgress(0);
    onDownload();

    // Simulate download progress
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsDownloading(false);
          setIsComplete(true);
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  const handleFinalDownload = () => {
    // This would trigger the actual file download
    window.open("https://example.com/video.mp4", "_blank");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.4 }}
      className="w-full max-w-2xl mx-auto"
    >
      <AnimatePresence mode="wait">
        {!isDownloading && !isComplete && (
          <motion.div
            key="download-button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Button
              onClick={handleDownload}
              disabled={disabled}
              className="w-full py-6 text-lg font-bold gradient-primary shadow-glow hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              size="lg"
            >
              <Download className="mr-2 h-6 w-6" />
              Start Download
            </Button>
          </motion.div>
        )}

        {isDownloading && (
          <motion.div
            key="downloading"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-card rounded-2xl p-6 border border-border shadow-card"
          >
            <div className="flex items-center gap-3 mb-4">
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
              <div>
                <h3 className="font-semibold">Processing your video...</h3>
                <p className="text-sm text-muted-foreground">Please wait while we prepare your download</p>
              </div>
            </div>
            <Progress value={progress} className="h-2" />
            <p className="text-right text-sm text-muted-foreground mt-2">{progress}%</p>
          </motion.div>
        )}

        {isComplete && (
          <motion.div
            key="complete"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-card rounded-2xl p-6 border-2 border-success shadow-card"
          >
            <div className="flex items-center gap-3 mb-4">
              <div className="bg-success/20 rounded-full p-2">
                <CheckCircle2 className="h-6 w-6 text-success" />
              </div>
              <div>
                <h3 className="font-semibold text-success">Your video is ready!</h3>
                <p className="text-sm text-muted-foreground">Click below to download your file</p>
              </div>
            </div>
            <Button
              onClick={handleFinalDownload}
              className="w-full py-6 text-base font-semibold bg-success hover:bg-success/90 text-success-foreground"
              size="lg"
            >
              <Download className="mr-2 h-5 w-5" />
              Download Video
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
