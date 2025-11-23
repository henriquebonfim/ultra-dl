import { useCallback, useState } from "react";
import { AdBanner } from "@/components/AdBanner";
import { DownloadButton } from "@/components/DownloadButton";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ResolutionPicker } from "@/components/ResolutionPicker";
import { UrlInput } from "@/components/UrlInput";
import { VideoPreview } from "@/components/VideoPreview";
import { toast } from "sonner";

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

interface VideoResolutionsResponse {
  meta: VideoMeta;
  formats: Resolution[];
}

const Index = () => {
  const [isValidated, setIsValidated] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState<Resolution | null>(null);
  const [availableResolutions, setAvailableResolutions] = useState<Resolution[]>([]);
  const [videoMeta, setVideoMeta] = useState<VideoMeta | null>(null);
  const [currentUrl, setCurrentUrl] = useState("");
  const [isDownloading, setIsDownloading] = useState(false);

  const API_URL = import.meta.env.VITE_API_URL;

  // Memoize event handler to prevent re-renders of UrlInput
  const handleVideoResolutionsSuccess = useCallback((data: VideoResolutionsResponse, url: string) => {
    setCurrentUrl(url);
    setVideoMeta(data.meta);
    setAvailableResolutions(data.formats);
    setIsValidated(true);
    setSelectedResolution(null);
  }, []);

  // Memoize event handler to prevent re-renders of ResolutionPicker
  const handleSelectResolution = useCallback((resolution: Resolution) => {
    setSelectedResolution(resolution);
  }, []);

  // Memoize event handler to prevent re-renders of DownloadButton
  const handleCreateJob = useCallback(async (): Promise<string | null> => {
    if (!selectedResolution || !currentUrl) return null;

    setIsDownloading(true);

    try {
      const response = await fetch(`${API_URL}/api/v1/downloads/`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: currentUrl,
          format_id: selectedResolution.format_id,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        toast.error(error.error || "Failed to create download job");
        setIsDownloading(false);
        return null;
      }

      const data = await response.json();
      return data.job_id;
    } catch (error) {
      console.error("Job creation error:", error);
      toast.error("Failed to create download job. Please try again.");
      setIsDownloading(false);
      return null;
    }
  }, [API_URL, currentUrl, selectedResolution]);

  // Memoize event handler to prevent re-renders of DownloadButton
  const handleJobComplete = useCallback(() => {
    setIsDownloading(false);
  }, []);

  // Memoize event handler to prevent re-renders of DownloadButton
  const handleJobCancel = useCallback(() => {
    setIsDownloading(false);
  }, []);

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 w-full px-4 pb-8">
        <div className="max-w-7xl mx-auto space-y-12">
          <AdBanner position="top" />

          <UrlInput onSuccess={handleVideoResolutionsSuccess} disabled={isDownloading} />

          {isValidated && availableResolutions.length > 0 && (
            <>
              {videoMeta && (
                <VideoPreview
                  videoId={videoMeta.id}
                  thumbnail={videoMeta.thumbnail}
                  title={videoMeta.title}
                  uploader={videoMeta.uploader}
                  duration={videoMeta.duration}
                />
              )}

              <ResolutionPicker
                onSelect={handleSelectResolution}
                selectedResolution={selectedResolution}
                availableResolutions={availableResolutions}
                disabled={isDownloading}
              />

              <DownloadButton
                disabled={!selectedResolution || isDownloading}
                onCreateJob={handleCreateJob}
                selectedResolution={selectedResolution}
                videoMeta={videoMeta}
                onJobCancel={handleJobCancel}
              />
            </>
          )}

          <AdBanner position="bottom" />
        </div>
      </main>

      <Footer />
    </div>
  );
};

export default Index;
