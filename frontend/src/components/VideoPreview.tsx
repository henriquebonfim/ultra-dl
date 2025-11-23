import { memo, useState } from "react";
import { motion } from "framer-motion";
import { Play, AlertCircle, Clock, User } from "lucide-react";

interface VideoPreviewProps {
  videoId: string;
  thumbnail: string;
  title: string;
  uploader?: string;
  duration?: number;
}

const extractVideoId = (url: string): string | null => {
  // Handle youtube.com/watch?v=VIDEO_ID
  const watchMatch = url.match(/[?&]v=([^&]+)/);
  if (watchMatch) return watchMatch[1];
  
  // Handle youtu.be/VIDEO_ID
  const shortMatch = url.match(/youtu\.be\/([^?]+)/);
  if (shortMatch) return shortMatch[1];
  
  // Handle youtube.com/embed/VIDEO_ID
  const embedMatch = url.match(/\/embed\/([^?]+)/);
  if (embedMatch) return embedMatch[1];
  
  return null;
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

const VideoPreviewComponent = ({ videoId, thumbnail, title, uploader, duration }: VideoPreviewProps) => {
  const [showEmbed, setShowEmbed] = useState(false);
  const [embedError, setEmbedError] = useState(false);

  const handlePlayClick = () => {
    setShowEmbed(true);
  };

  const handleEmbedError = () => {
    setEmbedError(true);
  };

  if (embedError) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-4xl mx-auto mb-8"
      >
        <div className="relative aspect-video bg-card border-2 border-border rounded-xl overflow-hidden flex items-center justify-center">
          <div className="text-center p-6">
            <AlertCircle className="h-12 w-12 text-muted-foreground mx-auto mb-3" />
            <p className="text-muted-foreground">Video preview unavailable</p>
            <p className="text-sm text-muted-foreground mt-1">The video may be private or restricted</p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
      className="w-full max-w-4xl mx-auto mb-8"
    >
      <div className="bg-card border-2 border-border rounded-xl overflow-hidden shadow-card">
        <div className="relative aspect-video">
          {!showEmbed ? (
            <button
              onClick={handlePlayClick}
              className="relative w-full h-full group cursor-pointer"
              aria-label={`Play ${title}`}
            >
              <img
                src={thumbnail}
                alt={title}
                className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
                onError={(e) => {
                  e.currentTarget.src = `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
                }}
              />
              <div className="absolute inset-0 bg-black/40 group-hover:bg-black/30 transition-colors duration-300" />
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="bg-primary rounded-full p-6 shadow-glow group-hover:scale-110 transition-transform duration-300">
                  <Play className="h-12 w-12 text-primary-foreground fill-current" />
                </div>
              </div>
            </button>
          ) : (
            <iframe
              src={`https://www.youtube.com/embed/${videoId}?autoplay=1`}
              title={title}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowFullScreen
              className="w-full h-full"
              onError={handleEmbedError}
            />
          )}
        </div>
        
        {/* Video Metadata */}
        <div className="p-4 space-y-2" data-testid="video-metadata">
          <h2 className="text-xl font-semibold line-clamp-2" data-testid="video-title">
            {title}
          </h2>
          
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            {uploader && (
              <div className="flex items-center gap-1.5" data-testid="video-uploader">
                <User className="h-4 w-4" />
                <span>{uploader}</span>
              </div>
            )}
            
            {duration !== undefined && (
              <div className="flex items-center gap-1.5" data-testid="video-duration">
                <Clock className="h-4 w-4" />
                <span>{formatDuration(duration)}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
};

VideoPreviewComponent.displayName = "VideoPreview";

export const VideoPreview = memo(VideoPreviewComponent);
