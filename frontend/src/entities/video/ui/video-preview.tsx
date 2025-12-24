import { VolumeX } from "lucide-react";
import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import YouTube, { YouTubePlayer, YouTubeProps } from "react-youtube";

interface VideoPreviewProps {
  videoId: string;
  startTime: number;
  endTime: number;
  currentTime?: number;
  muteAudio: boolean;
  muteVideo: boolean;
  onReady?: (event: { target: YouTubePlayer }) => void;
  onStateChange?: (event: { target: YouTubePlayer; data: number }) => void;
  onPlay?: () => void;
  onPause?: () => void;
}

export interface VideoPlayerRef {
  seekTo: (seconds: number) => void;
  pauseVideo: () => void;
  playVideo: () => void;
  getCurrentTime: () => Promise<number>;
}

export const VideoPreview = forwardRef<VideoPlayerRef, VideoPreviewProps>(({
  videoId,
  startTime,
  endTime,
  currentTime = 0,
  muteAudio,
  muteVideo,
  onReady,
  onStateChange,
  onPlay,
  onPause,
}, ref) => {
  const playerRef = useRef<YouTubePlayer | null>(null);

  useImperativeHandle(ref, () => ({
    seekTo: (seconds: number) => {
      playerRef.current?.seekTo(seconds);
    },
    pauseVideo: () => {
      playerRef.current?.pauseVideo();
    },
    playVideo: () => {
      playerRef.current?.playVideo();
    },
    getCurrentTime: async () => {
      return playerRef.current?.getCurrentTime() || 0;
    }
  }));

  // Handle mute state changes
  useEffect(() => {
    if (playerRef.current) {
      if (muteAudio) {
        playerRef.current.mute();
      } else {
        playerRef.current.unMute();
      }
    }
  }, [muteAudio]);

  const opts: YouTubeProps['opts'] = {
    height: '100%',
    width: '100%',
    playerVars: {
      start: Math.floor(startTime),
      rel: 0,
      modestbranding: 1,
      controls: 1,
      // We handle mute via API to start muted if needed
      mute: muteAudio ? 1 : 0,
    },
  };

  const handleReady = (event: { target: YouTubePlayer }) => {
    playerRef.current = event.target;
    if (muteAudio) {
      event.target.mute();
    }
    onReady?.(event);
  };

  const handleStateChange = (event: { target: YouTubePlayer; data: number }) => {
    onStateChange?.(event);

    // YouTube Player States:
    // -1 (unstarted)
    // 0 (ended)
    // 1 (playing)
    // 2 (paused)
    // 3 (buffering)
    // 5 (video cued)

    if (event.data === 1) {
      onPlay?.();
    } else if (event.data === 2) {
      onPause?.();
    }
  };

  if (muteVideo) {
    // Audio-only mode - show audio visualization placeholder
    return (
      <div
        className="relative w-full aspect-video rounded-xl bg-card border border-border overflow-hidden flex items-center justify-center"
        role="region"
        aria-label="Audio preview"
      >
        <div className="flex flex-col items-center gap-4">
          <div className="flex items-end gap-1 h-16">
            {[...Array(12)].map((_, i) => (
              <div
                key={i}
                className="w-2 bg-gradient-primary rounded-full animate-pulse"
                style={{
                  height: `${20 + Math.random() * 60}%`,
                  animationDelay: `${i * 0.1}s`,
                }}
              />
            ))}
          </div>
          <p className="text-muted-foreground text-sm">Audio Only Mode</p>
          {/* We still need the player for audio, just hidden */}
          <div className="hidden">
             <YouTube
              videoId={videoId}
              opts={opts}
              onReady={handleReady}
              onStateChange={handleStateChange}
              className="w-0 h-0 opacity-0"
            />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="relative w-full aspect-video rounded-xl bg-card border border-border overflow-hidden"
      role="region"
      aria-label="Video preview"
    >
      <YouTube
        videoId={videoId}
        opts={opts}
        onReady={handleReady}
        onStateChange={handleStateChange}
        className="w-full h-full"
        iframeClassName="w-full h-full"
      />
      {muteAudio && (
        <div className="absolute top-4 right-4 bg-background/80 backdrop-blur-sm rounded-full p-2 pointer-events-none z-10">
          <VolumeX className="h-5 w-5 text-muted-foreground" aria-label="Audio muted" />
        </div>
      )}
    </div>
  );
});

VideoPreview.displayName = "VideoPreview";
