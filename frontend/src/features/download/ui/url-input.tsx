import { useState } from "react";
import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { PlayCircle, Search, Loader2 } from "lucide-react";

interface UrlInputProps {
  onSubmit: (url: string) => void;
  isLoading: boolean;
  disabled?: boolean;
}

export const UrlInput = ({ onSubmit, isLoading, disabled }: UrlInputProps) => {
  const [url, setUrl] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onSubmit(url.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="bg-card/50 border border-primary/30 rounded-2xl p-6 space-y-4">
        <div className="relative">
          <PlayCircle
            className="absolute left-4 top-1/2 -translate-y-1/2 text-muted-foreground"
            size={20}
            aria-hidden="true"
          />
          <Input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=cZkW-UuN0i4"
            className="pl-12 h-14 text-base bg-secondary border-0 rounded-xl focus:ring-primary/20 transition-all"
            aria-label="YouTube URL"
            disabled={disabled}
          />
        </div>
        <Button
          type="submit"
          disabled={isLoading || !url.trim() || disabled}
          className="w-full h-14 text-base font-semibold bg-gradient-primary hover:opacity-90 transition-opacity rounded-xl"
          aria-label={isLoading ? "Loading..." : "Check URL"}
        >
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading
            </>
          ) : (
            <>
              <Search className="mr-2 h-5 w-5" />
              Check URL
            </>
          )}
        </Button>
      </div>
    </form>
  );
};