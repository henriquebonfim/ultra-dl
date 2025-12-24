import { VideoPlayerRef, VideoPreview } from "@/entities/video/ui/video-preview";
import { DownloadOptions } from "@/features/download/ui/download-options";
import { DownloadProgress } from "@/features/download/ui/download-progress";
import { FileNameInput } from "@/features/download/ui/file-name-input";
import { TrimControls } from "@/features/download/ui/trim-controls";
import { UrlInput } from "@/features/download/ui/url-input";
import { useToast } from "@/shared/hooks/use-toast";
import { AdBanner } from "@/shared/ui/ad-banner";
import { Button } from "@/shared/ui/button";
import { ErrorMessage } from "@/shared/ui/error-message";
import { Footer } from "@/widgets/footer/ui/footer";
import { Download } from "lucide-react";
import { useEffect, useRef, useState } from "react";

// Integration Hooks
import { createJob } from "@/entities/job/api/createJob";
import { useJobStatus } from "@/entities/job/api/useJobStatus";
import type { VideoFormat, VideoInfo as VideoInfoType } from "@/entities/video/model/types";
import { useDownload } from "@/features/download/model/useDownload";
import { useUrlValidation } from "@/features/url-validation/model/useUrlValidation";

// App State
type AppState = "initial" | "preview" | "processing" | "complete" | "error";

const Index = () => {
  const { toast } = useToast();
  const [appState, setAppState] = useState<AppState>("initial");
  const playerRef = useRef<VideoPlayerRef>(null);

  // Feature Hooks
  const { validateUrl, isValidating } = useUrlValidation();
  const { createJob: startDownload, deleteJob, handleDownloadFile, handleExpire, resetJob, jobId } = useDownload();
  const { data: jobStatus, disconnect } = useJobStatus(jobId);

  // Video Data
  const [videoInfo, setVideoInfo] = useState<VideoInfoType | null>(null);
  const [availableFormats, setAvailableFormats] = useState<VideoFormat[]>([]);
  const [videoUrl, setVideoUrl] = useState("");
  const [error, setError] = useState<{ title: string; message: string } | null>(null);

  // Video Options
  const [startTime, setStartTime] = useState(0);
  const [endTime, setEndTime] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [muteAudio, setMuteAudio] = useState(false);
  const [muteVideo, setMuteVideo] = useState(false);
  const [quality, setQuality] = useState("1080");
  const [format, setFormat] = useState("mp4");
  const [fileName, setFileName] = useState("");

  // Handle URL Submission
  const handleUrlSubmit = async (url: string) => {
    setError(null);
    const { result, data } = await validateUrl(url);

    if (result.isValid && data) {
      setVideoInfo(data.meta);
      setAvailableFormats(data.formats);
      setVideoUrl(url);
      setEndTime(data.meta.duration);

      // Extract start time from URL parameter 't'
      let initialStartTime = 0;
      try {
        const urlObj = new URL(url);
        const tParam = urlObj.searchParams.get("t");
        if (tParam) {
          // Handle '863s' -> 863, or '863' -> 863
          const seconds = parseInt(tParam.replace("s", ""), 10);
          if (!isNaN(seconds)) {
            initialStartTime = seconds;
          }
        }
      } catch (e) {
        // Ignore parsing errors
      }

      setStartTime(initialStartTime);
      setCurrentTime(initialStartTime);
      setFileName(data.meta.title.replace(/[^a-z0-9]/gi, '_').toLowerCase());
      setAppState("preview");
    } else {
      // Error is handled by hook toasts, but we could set generic error state here if desired
    }
  };

  // Handle Download Process
  const handleProcess = async () => {
    if (!videoUrl) return;

    setAppState("processing");

    // Create Job Request
    const isFullDuration = videoInfo && startTime === 0 && endTime === videoInfo.duration;

    const request = {
      url: videoUrl,
      quality: quality,
      format: format,
      muteAudio: muteAudio,
      muteVideo: muteVideo,
      startTime: isFullDuration ? undefined : startTime,
      endTime: isFullDuration ? undefined : endTime,
    };

    const newJobId = await startDownload(async () => {
      try {
        const response = await createJob(request);
        return response.job_id;
      } catch (err) {
        setAppState("initial");
        throw err;
      }
    });

    if (newJobId) {
      toast({
        title: "Processing started",
        description: "Your video is being processed...",
      });
    }
  };

  // Monitor Job Status
  useEffect(() => {
    if (jobStatus) {
      if (jobStatus.status === "completed") {
        setAppState("complete");
      } else if (jobStatus.status === "failed") {
        setAppState("preview");
      }
    }
  }, [jobStatus]);

  const handleRetry = () => {
    setAppState("initial");
    setError(null);
    setVideoInfo(null);
    setVideoUrl("");
    resetJob();
    disconnect();
  };

  const currentExtension = muteVideo ? (format === "mp4" ? "mp3" : format) : format;
  const fullFileName = `${fileName}.${currentExtension}`;

  const getEstimatedTime = (): string | undefined => {
    if (jobStatus?.time_remaining) {
      if (jobStatus.time_remaining < 60) return `${jobStatus.time_remaining}s remaining`;
      return `${Math.ceil(jobStatus.time_remaining / 60)}m remaining`;
    }
    return undefined;
  };

  // Sync Player with Controls
  const handleStartTimeChange = (time: number) => {
    setStartTime(time);
    playerRef.current?.seekTo(time);
    playerRef.current?.pauseVideo();
    setCurrentTime(time);
  };

  const handleEndTimeChange = (time: number) => {
    setEndTime(time);
    playerRef.current?.seekTo(time);
    playerRef.current?.pauseVideo();
    setCurrentTime(time);
  };

  const handleCurrentTimeChange = (time: number) => {
    setCurrentTime(time);
    playerRef.current?.seekTo(time);
  };

  // Poll for current time during playback
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isPlaying) {
      interval = setInterval(async () => {
        if (playerRef.current) {
          const time = await playerRef.current.getCurrentTime();
          setCurrentTime(time);

          // Loop if we hit end time
          if (endTime > 0 && time >= endTime) {
            playerRef.current.pauseVideo();
            playerRef.current.seekTo(startTime);
            setIsPlaying(false);
          }
        }
      }, 500);
    }
    return () => clearInterval(interval);
  }, [isPlaying, endTime, startTime]);

  const handlePlayerStateChange = (event: any) => {
    // 1 = playing, 2 = paused
    if (event.data === 1) setIsPlaying(true);
    if (event.data === 2) setIsPlaying(false);
  };

  const handlePlayPause = () => {
    if (isPlaying) {
      playerRef.current?.pauseVideo();
    } else {
      playerRef.current?.playVideo();
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-dark">
      <header className="w-full py-8 text-center">
        <div className="flex items-center justify-center gap-2 mb-2">
          <div className="w-10 h-10 rounded-lg bg-primary/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-primary" viewBox="0 0 24 24" fill="currentColor">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <h1 className="text-4xl md:text-5xl font-bold bg-gradient-primary bg-clip-text text-transparent">
            UltraDL
          </h1>
        </div>
        <p className="text-muted-foreground max-w-lg mx-auto px-4">
          Download your favorite YouTube videos, podcasts, and music.
        </p>
      </header>

      <main className="flex-1 container max-w-4xl mx-auto px-4 py-8 space-y-8">
        <AdBanner />

        <UrlInput
          onSubmit={handleUrlSubmit}
          isLoading={isValidating}
          disabled={appState === "processing"}
        />

        {appState === "error" && error && (
          <ErrorMessage
            title={error.title}
            message={error.message}
            onRetry={handleRetry}
          />
        )}

        {(appState === "preview" || appState === "processing" || appState === "complete") && videoInfo && (
          <div className="space-y-6 animate-in fade-in-50 duration-500">
            <FileNameInput
              fileName={fileName}
              extension={currentExtension}
              onChange={setFileName}
            />

            <VideoPreview
              ref={playerRef}
              videoId={videoInfo.id}
              startTime={startTime}
              endTime={endTime}
              currentTime={currentTime}
              muteAudio={muteAudio}
              muteVideo={muteVideo}
              onStateChange={handlePlayerStateChange}
            />

            {appState === "preview" && (
              <>
                <DownloadOptions
                  muteAudio={muteAudio}
                  muteVideo={muteVideo}
                  quality={quality}
                  format={format}
                  onMuteAudioChange={setMuteAudio}
                  onMuteVideoChange={setMuteVideo}
                  onQualityChange={setQuality}
                  onFormatChange={setFormat}
                  availableFormats={availableFormats}
                />

                <TrimControls
                  duration={videoInfo.duration}
                  startTime={startTime}
                  endTime={endTime}
                  currentTime={currentTime}
                  isPlaying={isPlaying}
                  onStartTimeChange={handleStartTimeChange}
                  onEndTimeChange={handleEndTimeChange}
                  onCurrentTimeChange={handleCurrentTimeChange}
                  onPlayPause={handlePlayPause}
                />

                <Button
                  onClick={handleProcess}
                  size="lg"
                  className="w-full h-14 text-lg font-semibold bg-gradient-primary hover:opacity-90 transition-opacity"
                >
                  <Download className="mr-2 h-5 w-5" />
                  Process & Download
                </Button>
              </>
            )}

            {(appState === "processing" || appState === "complete") && (
              <DownloadProgress
                progress={jobStatus?.progress?.percentage || 0}
                fileName={fullFileName}
                estimatedTime={getEstimatedTime()}
                downloadUrl={jobStatus?.download_url}
                isProcessing={appState === "processing"}
                phase={jobStatus?.progress?.phase}
              />
            )}

            {appState === "complete" && (
              <Button
                variant="outline"
                onClick={handleRetry}
                className="w-full"
              >
                Process Another Video
              </Button>
            )}
          </div>
        )}

        <AdBanner className="mt-8" />
      </main>

      <Footer />
    </div>
  );
};

export default Index;
