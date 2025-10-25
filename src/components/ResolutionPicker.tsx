import { motion } from "framer-motion";
import { Video, FileVideo, Check } from "lucide-react";

interface Resolution {
  id: string;
  resolution: string;
  fileSize: string;
  quality: string;
  hasAudio: boolean;
}

interface ResolutionPickerProps {
  onSelect: (resolution: Resolution) => void;
  selectedResolution: Resolution | null;
}

const mockResolutions: Resolution[] = [
  { id: "1", resolution: "720p HD", fileSize: "45 MB", quality: "Good", hasAudio: true },
  { id: "2", resolution: "1080p Full HD", fileSize: "98 MB", quality: "Great", hasAudio: true },
  { id: "3", resolution: "1440p 2K", fileSize: "156 MB", quality: "Excellent", hasAudio: true },
  { id: "4", resolution: "2160p 4K", fileSize: "312 MB", quality: "Ultra", hasAudio: true },
  { id: "5", resolution: "4320p 8K", fileSize: "645 MB", quality: "Premium", hasAudio: false },
];

export const ResolutionPicker = ({ onSelect, selectedResolution }: ResolutionPickerProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.3 }}
      className="w-full max-w-4xl mx-auto"
    >
      <h2 className="text-2xl font-bold text-center mb-6">Choose Resolution</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mockResolutions.map((res, index) => (
          <motion.button
            key={res.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 * index }}
            onClick={() => onSelect(res)}
            className={`relative bg-card border-2 rounded-xl p-5 transition-all duration-300 hover:scale-105 hover:shadow-glow ${
              selectedResolution?.id === res.id
                ? "border-primary shadow-glow"
                : "border-border hover:border-primary/50"
            }`}
          >
            {selectedResolution?.id === res.id && (
              <div className="absolute -top-2 -right-2 bg-primary rounded-full p-1">
                <Check className="h-4 w-4 text-primary-foreground" />
              </div>
            )}
            
            <div className="flex items-start gap-3 mb-3">
              {res.hasAudio ? (
                <Video className="h-6 w-6 text-primary flex-shrink-0" />
              ) : (
                <FileVideo className="h-6 w-6 text-accent flex-shrink-0" />
              )}
              <div className="text-left flex-1">
                <h3 className="font-bold text-lg">{res.resolution}</h3>
                <p className="text-sm text-muted-foreground">{res.quality}</p>
              </div>
            </div>
            
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">{res.fileSize}</span>
              <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                res.hasAudio ? "bg-primary/20 text-primary" : "bg-accent/20 text-accent"
              }`}>
                {res.hasAudio ? "Video + Audio" : "Video Only"}
              </span>
            </div>
          </motion.button>
        ))}
      </div>
    </motion.div>
  );
};
