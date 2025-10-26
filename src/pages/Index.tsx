import { useState } from "react";
import { Header } from "@/components/Header";
import { AdBanner } from "@/components/AdBanner";
import { UrlInput } from "@/components/UrlInput";
import { ResolutionPicker } from "@/components/ResolutionPicker";
import { DownloadButton } from "@/components/DownloadButton";
import { Footer } from "@/components/Footer";
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

const Index = () => {
  const [isValidated, setIsValidated] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState<Resolution | null>(null);
  const [availableResolutions, setAvailableResolutions] = useState<Resolution[]>([]);
  const [videoMeta, setVideoMeta] = useState<VideoMeta | null>(null);
  const [currentUrl, setCurrentUrl] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleValidate = async (url: string) => {
    setIsLoading(true);
    setCurrentUrl(url);
    try {
      const response = await fetch("http://localhost:8000/api/resolutions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const error = await response.json();
        toast.error(error.error || "Failed to fetch video information");
        setIsLoading(false);
        return;
      }

      const data = await response.json();
      setVideoMeta(data.meta);
      setAvailableResolutions(data.formats);
      setIsValidated(true);
      setIsLoading(false);
    } catch (error) {
      console.error("Error fetching resolutions:", error);
      toast.error("Failed to connect to the backend. Make sure it's running.");
      setIsLoading(false);
    }
  };

  const handleSelectResolution = (resolution: Resolution) => {
    setSelectedResolution(resolution);
  };

  const handleDownload = async () => {
    if (!selectedResolution || !currentUrl) return;
    
    try {
      const response = await fetch("http://localhost:8000/api/download", {
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
        toast.error(error.error || "Download failed");
        return;
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = `${videoMeta?.title || "video"}.${selectedResolution.ext}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(downloadUrl);
      document.body.removeChild(a);
      toast.success("Download started!");
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Download failed. Please try again.");
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 w-full px-4 pb-8">
        <div className="max-w-7xl mx-auto space-y-12">
          <AdBanner position="top" />
          
          <UrlInput onValidate={handleValidate} isLoading={isLoading} />
          
          {isValidated && availableResolutions.length > 0 && (
            <>
              {videoMeta && (
                <div className="text-center mb-4" data-testid="video-meta">
                  <h2 className="text-xl font-semibold" data-testid="text-video-title">{videoMeta.title}</h2>
                  <p className="text-sm text-muted-foreground" data-testid="text-video-uploader">{videoMeta.uploader}</p>
                </div>
              )}
              
              <ResolutionPicker
                onSelect={handleSelectResolution}
                selectedResolution={selectedResolution}
                availableResolutions={availableResolutions}
              />
              
              <DownloadButton
                disabled={!selectedResolution}
                onDownload={handleDownload}
                selectedResolution={selectedResolution}
                videoMeta={videoMeta}
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
