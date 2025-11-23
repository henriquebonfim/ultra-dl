import { memo, useMemo } from "react";
import { motion } from "framer-motion";
import { Video, FileVideo, Music, Check, Info } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

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
  disabled?: boolean;
}

enum FormatType {
  VIDEO_AUDIO = "video+audio",
  VIDEO_ONLY = "video_only",
  AUDIO_ONLY = "audio_only"
}

interface GroupedFormats {
  [FormatType.VIDEO_AUDIO]: Resolution[];
  [FormatType.VIDEO_ONLY]: Resolution[];
  [FormatType.AUDIO_ONLY]: Resolution[];
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

const getFormatType = (res: Resolution): FormatType => {
  const hasAudio = res.acodec !== "none";
  const hasVideo = res.vcodec !== "none";
  
  if (hasAudio && hasVideo) return FormatType.VIDEO_AUDIO;
  if (hasVideo) return FormatType.VIDEO_ONLY;
  return FormatType.AUDIO_ONLY;
};

const groupFormatsByType = (resolutions: Resolution[]): GroupedFormats => {
  const grouped: GroupedFormats = {
    [FormatType.VIDEO_AUDIO]: [],
    [FormatType.VIDEO_ONLY]: [],
    [FormatType.AUDIO_ONLY]: []
  };

  resolutions.forEach(res => {
    const type = getFormatType(res);
    grouped[type].push(res);
  });

  // Sort each group by height descending
  Object.keys(grouped).forEach(key => {
    grouped[key as FormatType].sort((a, b) => b.height - a.height);
  });

  return grouped;
};

const getGroupIcon = (type: FormatType) => {
  switch (type) {
    case FormatType.VIDEO_AUDIO:
      return <Video className="h-5 w-5" />;
    case FormatType.VIDEO_ONLY:
      return <FileVideo className="h-5 w-5" />;
    case FormatType.AUDIO_ONLY:
      return <Music className="h-5 w-5" />;
  }
};

const getGroupTitle = (type: FormatType) => {
  switch (type) {
    case FormatType.VIDEO_AUDIO:
      return "Video + Audio";
    case FormatType.VIDEO_ONLY:
      return "Video Only";
    case FormatType.AUDIO_ONLY:
      return "Audio Only";
  }
};

const getGroupDescription = (type: FormatType) => {
  switch (type) {
    case FormatType.VIDEO_AUDIO:
      return "Complete video with sound";
    case FormatType.VIDEO_ONLY:
      return "Video without audio track";
    case FormatType.AUDIO_ONLY:
      return "Audio track only";
  }
};

const getCodecInfo = (res: Resolution): string => {
  const parts: string[] = [];
  
  if (res.vcodec && res.vcodec !== "none") {
    parts.push(`Video: ${res.vcodec}`);
  }
  
  if (res.acodec && res.acodec !== "none") {
    parts.push(`Audio: ${res.acodec}`);
  }
  
  return parts.join(" • ");
};

const getCompatibilityNote = (res: Resolution): string => {
  const ext = res.ext.toLowerCase();
  
  if (ext === "mp4") {
    return "Universal compatibility - works on all devices";
  } else if (ext === "webm") {
    return "Modern format - best for web playback";
  } else if (ext === "mkv") {
    return "High quality container - may need special player";
  } else if (ext === "m4a") {
    return "Audio format - compatible with most players";
  }
  
  return "Standard format";
};

const ResolutionPickerComponent = ({ onSelect, selectedResolution, availableResolutions, disabled = false }: ResolutionPickerProps) => {
  // Memoize filtered resolutions to avoid recalculating on every render
  const filteredResolutions = useMemo(() => {
    return availableResolutions.filter(
      res => res.vcodec !== "none" || res.acodec !== "none"
    );
  }, [availableResolutions]);
  
  // Memoize grouped formats to avoid expensive sorting on every render
  const groupedFormats = useMemo(() => {
    return groupFormatsByType(filteredResolutions);
  }, [filteredResolutions]);
  
  // Memoize groups to show to avoid filtering on every render
  const groupsToShow = useMemo(() => {
    return [
      FormatType.VIDEO_AUDIO,
      FormatType.VIDEO_ONLY,
      FormatType.AUDIO_ONLY
    ].filter(type => groupedFormats[type].length > 0);
  }, [groupedFormats]);

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.3 }}
        className="w-full max-w-6xl mx-auto"
      >
        <h2 className="text-2xl font-bold text-center mb-8">Choose Format</h2>
        
        <div className="space-y-8">
          {groupsToShow.map((type, groupIndex) => {
            const formats = groupedFormats[type];
            
            return (
              <motion.div
                key={type}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.1 * groupIndex }}
                className="space-y-4"
              >
                <div className="flex items-center gap-3 px-2">
                  <div className="text-primary">
                    {getGroupIcon(type)}
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold">{getGroupTitle(type)}</h3>
                    <p className="text-sm text-muted-foreground">{getGroupDescription(type)}</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {formats.map((res, index) => {
                    const hasAudio = res.acodec !== "none";
                    const hasVideo = res.vcodec !== "none";
                    const quality = getQualityLabel(res.height);
                    const codecInfo = getCodecInfo(res);
                    const compatibilityNote = getCompatibilityNote(res);
                    
                    return (
                      <motion.div
                        key={res.format_id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, delay: 0.05 * index }}
                      >
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <button
                              onClick={() => !disabled && onSelect(res)}
                              disabled={disabled}
                              className={`relative w-full bg-card border-2 rounded-xl p-5 transition-all duration-300 ${
                                disabled 
                                  ? "opacity-50 cursor-not-allowed" 
                                  : "hover:scale-105 hover:shadow-glow"
                              } ${
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
                              
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <div className="absolute top-3 right-3">
                                    <Info className="h-4 w-4 text-muted-foreground hover:text-primary transition-colors" />
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent side="left" className="max-w-xs">
                                  <div className="space-y-2">
                                    <div>
                                      <p className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-1">Codecs</p>
                                      <p className="text-sm">{codecInfo || "Standard codecs"}</p>
                                    </div>
                                    <div>
                                      <p className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-1">Compatibility</p>
                                      <p className="text-sm">{compatibilityNote}</p>
                                    </div>
                                    {res.filesize && (
                                      <div>
                                        <p className="font-semibold text-xs uppercase tracking-wide text-muted-foreground mb-1">File Size</p>
                                        <p className="text-sm">{formatFileSize(res.filesize)}</p>
                                      </div>
                                    )}
                                  </div>
                                </TooltipContent>
                              </Tooltip>
                              
                              <div className="flex items-start gap-3 mb-3">
                                {hasAudio && hasVideo ? (
                                  <Video className="h-6 w-6 text-primary flex-shrink-0" />
                                ) : hasVideo ? (
                                  <FileVideo className="h-6 w-6 text-accent flex-shrink-0" />
                                ) : (
                                  <Music className="h-6 w-6 text-accent flex-shrink-0" />
                                )}
                                <div className="text-left flex-1 pr-6">
                                  <h3 className="font-bold text-lg">{res.resolution}</h3>
                                  <p className="text-sm text-muted-foreground">{quality}</p>
                                  {res.note && <p className="text-xs text-muted-foreground">{res.note}</p>}
                                </div>
                              </div>
                              
                              <div className="flex items-center justify-between text-sm">
                                <span className="text-muted-foreground">{formatFileSize(res.filesize)}</span>
                                <span className="text-xs text-muted-foreground uppercase tracking-wide">
                                  {res.ext}
                                </span>
                              </div>
                            </button>
                          </TooltipTrigger>
                        </Tooltip>
                      </motion.div>
                    );
                  })}
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </TooltipProvider>
  );
};

ResolutionPickerComponent.displayName = "ResolutionPicker";

export const ResolutionPicker = memo(ResolutionPickerComponent);
