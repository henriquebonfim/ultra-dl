import { useState } from "react";
import { Header } from "@/components/Header";
import { AdBanner } from "@/components/AdBanner";
import { UrlInput } from "@/components/UrlInput";
import { ResolutionPicker } from "@/components/ResolutionPicker";
import { DownloadButton } from "@/components/DownloadButton";
import { Footer } from "@/components/Footer";

interface Resolution {
  id: string;
  resolution: string;
  fileSize: string;
  quality: string;
  hasAudio: boolean;
}

const Index = () => {
  const [isValidated, setIsValidated] = useState(false);
  const [selectedResolution, setSelectedResolution] = useState<Resolution | null>(null);

  const handleValidate = (url: string) => {
    console.log("Validating URL:", url);
    setIsValidated(true);
  };

  const handleSelectResolution = (resolution: Resolution) => {
    setSelectedResolution(resolution);
  };

  const handleDownload = () => {
    console.log("Starting download for:", selectedResolution);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      
      <main className="flex-1 w-full px-4 pb-8">
        <div className="max-w-7xl mx-auto space-y-12">
          <AdBanner position="top" />
          
          <UrlInput onValidate={handleValidate} />
          
          {isValidated && (
            <>
              <ResolutionPicker
                onSelect={handleSelectResolution}
                selectedResolution={selectedResolution}
              />
              
              <DownloadButton
                disabled={!selectedResolution}
                onDownload={handleDownload}
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
