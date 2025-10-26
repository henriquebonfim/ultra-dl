import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Download, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

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
  onDownload: () => void;
  selectedResolution: Resolution | null;
  videoMeta: VideoMeta | null;
}

export const DownloadButton = ({ disabled, onDownload, selectedResolution, videoMeta }: DownloadButtonProps) => {
  const [isDownloading, setIsDownloading] = useState(false);

  const handleDownload = async () => {
    setIsDownloading(true);
    try {
      await onDownload();
    } finally {
      setIsDownloading(false);
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
        {!isDownloading && (
          <motion.div
            key="download-button"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <Button
              onClick={handleDownload}
              disabled={disabled || isDownloading}
              className="w-full py-6 text-lg font-bold gradient-primary shadow-glow hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
              size="lg"
              data-testid="button-download"
            >
              <Download className="mr-2 h-6 w-6" />
              Download {selectedResolution?.resolution || "Video"}
            </Button>
            {selectedResolution && videoMeta && (
              <p className="text-center text-sm text-muted-foreground mt-3" data-testid="text-download-info">
                Ready to download: {videoMeta.title} ({selectedResolution.resolution})
              </p>
            )}
          </motion.div>
        )}

        {isDownloading && (
          <motion.div
            key="downloading"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="bg-card rounded-2xl p-6 border border-border shadow-card"
            data-testid="status-downloading"
          >
            <div className="flex items-center gap-3">
              <Loader2 className="h-6 w-6 text-primary animate-spin" />
              <div>
                <h3 className="font-semibold">Downloading your video...</h3>
                <p className="text-sm text-muted-foreground">This may take a moment depending on the video size</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
