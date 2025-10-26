import { useState } from "react";
import { motion } from "framer-motion";
import { Youtube, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";

interface UrlInputProps {
  onValidate: (url: string) => void;
  isLoading?: boolean;
}

export const UrlInput = ({ onValidate, isLoading = false }: UrlInputProps) => {
  const [url, setUrl] = useState("");
  const [isInvalid, setIsInvalid] = useState(false);

  const validateYoutubeUrl = (url: string): boolean => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    return youtubeRegex.test(url);
  };

  const handleCheck = () => {
    if (!url.trim()) {
      setIsInvalid(true);
      toast.error("Please paste a YouTube URL");
      return;
    }

    if (!validateYoutubeUrl(url)) {
      setIsInvalid(true);
      toast.error("Invalid YouTube URL");
      return;
    }

    setIsInvalid(false);
    toast.success("Video found! Select your resolution below.");
    onValidate(url);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, delay: 0.2 }}
      className="w-full max-w-3xl mx-auto"
    >
      <div className="bg-card shadow-card rounded-2xl p-6 md:p-8 border border-border">
        <div className="flex flex-col gap-4">
          <div className="relative">
            <Youtube className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Paste your YouTube link here..."
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setIsInvalid(false);
              }}
              onKeyDown={(e) => e.key === "Enter" && handleCheck()}
              className={`pl-12 pr-4 py-6 text-base bg-input border-2 transition-all duration-300 ${
                isInvalid
                  ? "border-destructive focus-visible:ring-destructive"
                  : "border-border focus-visible:ring-primary"
              }`}
              data-testid="input-youtube-url"
            />
          </div>
          <Button
            onClick={handleCheck}
            disabled={isLoading}
            className="w-full py-6 text-base font-semibold gradient-primary shadow-glow hover:opacity-90 transition-opacity"
            size="lg"
            data-testid="button-check-video"
          >
            <Search className="mr-2 h-5 w-5" />
            {isLoading ? "Checking..." : "Check Video"}
          </Button>
        </div>
      </div>
    </motion.div>
  );
};
