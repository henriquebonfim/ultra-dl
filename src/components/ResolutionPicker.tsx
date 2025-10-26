import { motion } from "framer-motion";
import { Video, FileVideo, Check } from "lucide-react";

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

interface ResolutionPickerProps {
  onSelect: (resolution: Resolution) => void;
  selectedResolution: Resolution | null;
  availableResolutions: Resolution[];
}

const formatFileSize = (bytes: number | null): string => {
  if (!bytes) return "Unknown";
  const mb = bytes / (1024 * 1024);
  if (mb < 1024) {
    return `${Math.round(mb)} MB`;
  }
  return `${(mb / 1024).toFixed(1)} GB`;
};

const getQualityLabel = (height: number): string => {
  if (height >= 2160) return "Ultra";
  if (height >= 1440) return "Excellent";
  if (height >= 1080) return "Great";
  if (height >= 720) return "Good";
  return "Standard";
};

export const ResolutionPicker = ({ onSelect, selectedResolution, availableResolutions }: ResolutionPickerProps) => {
  const filteredResolutions = availableResolutions.filter(
    res => res.vcodec !== "none" || res.acodec !== "none"
  ).slice(0, 10);
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.3 }}
      className="w-full max-w-4xl mx-auto"
    >
      <h2 className="text-2xl font-bold text-center mb-6">Choose Resolution</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredResolutions.map((res, index) => {
          const hasAudio = res.acodec !== "none";
          const hasVideo = res.vcodec !== "none";
          const quality = getQualityLabel(res.height);
          
          return (
            <motion.button
              key={res.format_id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.4, delay: 0.1 * index }}
              onClick={() => onSelect(res)}
              className={`relative bg-card border-2 rounded-xl p-5 transition-all duration-300 hover:scale-105 hover:shadow-glow ${
                selectedResolution?.format_id === res.format_id
                  ? "border-primary shadow-glow"
                  : "border-border hover:border-primary/50"
              }`}
              data-testid={`button-resolution-${res.format_id}`}
            >
              {selectedResolution?.format_id === res.format_id && (
                <div className="absolute -top-2 -right-2 bg-primary rounded-full p-1">
                  <Check className="h-4 w-4 text-primary-foreground" />
                </div>
              )}
              
              <div className="flex items-start gap-3 mb-3">
                {hasAudio && hasVideo ? (
                  <Video className="h-6 w-6 text-primary flex-shrink-0" />
                ) : (
                  <FileVideo className="h-6 w-6 text-accent flex-shrink-0" />
                )}
                <div className="text-left flex-1">
                  <h3 className="font-bold text-lg">{res.resolution}</h3>
                  <p className="text-sm text-muted-foreground">{quality}</p>
                  {res.note && <p className="text-xs text-muted-foreground">{res.note}</p>}
                </div>
              </div>
              
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{formatFileSize(res.filesize)}</span>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                  hasAudio && hasVideo ? "bg-primary/20 text-primary" : "bg-accent/20 text-accent"
                }`}>
                  {hasAudio && hasVideo ? "Video + Audio" : hasAudio ? "Audio Only" : "Video Only"}
                </span>
              </div>
            </motion.button>
          );
        })}
      </div>
    </motion.div>
  );
};
