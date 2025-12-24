import { VideoFormat } from "@/entities/video/model/types";
import { Checkbox } from "@/shared/ui/checkbox";
import { Label } from "@/shared/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/ui/select";
import { MonitorOff, VolumeX } from "lucide-react";
import { useMemo } from "react";

interface DownloadOptionsProps {
  muteAudio: boolean;
  muteVideo: boolean;
  quality: string;
  format: string;
  onMuteAudioChange: (muted: boolean) => void;
  onMuteVideoChange: (muted: boolean) => void;
  onQualityChange: (quality: string) => void;
  onFormatChange: (format: string) => void;
  availableFormats: VideoFormat[];
}

const audioFormats = [
  { value: "mp3", label: "MP3" },
  { value: "aac", label: "AAC" },
  { value: "wav", label: "WAV" },
  { value: "ogg", label: "OGG" },
];

export const DownloadOptions = ({
  muteAudio,
  muteVideo,
  quality,
  format,
  onMuteAudioChange,
  onMuteVideoChange,
  onQualityChange,
  onFormatChange,
  availableFormats,
}: DownloadOptionsProps) => {
  const isAudioOnly = muteVideo && !muteAudio;

  // Derive dynamic options from availableFormats
  const { qualities, formats } = useMemo(() => {
    // 1. Extract unique resolutions (heights)
    const uniqueHeights = new Set<number>();
    availableFormats.forEach(f => {
      // Filter out invalid or audio-only formats when looking for video qualities
      if (f.height && f.vcodec !== 'none') {
        uniqueHeights.add(f.height);
      }
    });

    const sortedQualities = Array.from(uniqueHeights)
      .sort((a, b) => b - a) // Descending order
      .map(height => {
        let label = `${height}p`;
        if (height >= 4320) label = `8K (${height}p)`;
        else if (height >= 2160) label = `4K (${height}p)`;
        else if (height >= 1440) label = `2K (${height}p)`;
        else if (height >= 1080) label = `FHD (${height}p)`;
        else if (height >= 720) label = `HD (${height}p)`;
        else if (height >= 480) label = `SD (${height}p)`;

        return { value: height.toString(), label };
      });

    // 2. Formats
    const standardFormats = [
      { value: "mp4", label: "MP4" },
      { value: "webm", label: "WebM" },
      { value: "mkv", label: "MKV" },
      { value: "avi", label: "AVI" },
    ];

    return { qualities: sortedQualities, formats: standardFormats };
  }, [availableFormats]);

  return (
    <div className="flex flex-wrap gap-6 justify-between">

      <div className="flex items-center space-x-3">
        <Checkbox
          id="mute-video"
          checked={muteVideo}
          onCheckedChange={(checked) => onMuteVideoChange(checked as boolean)}
          disabled={muteAudio}
          aria-describedby="mute-video-desc"
        />
        <div className="flex items-center gap-2">
          <MonitorOff className="h-4 w-4 text-muted-foreground" />
          <Label
            htmlFor="mute-video"
            className="text-sm font-medium cursor-pointer"
          >
            Remove Video
          </Label>
        </div>
        <span id="mute-video-desc" className="sr-only">
          Download audio only without video
        </span>
      </div>

      <div className="flex items-center space-x-3">
        <Checkbox
          id="mute-audio"
          checked={muteAudio}
          onCheckedChange={(checked) => onMuteAudioChange(checked as boolean)}
          disabled={muteVideo}
          aria-describedby="mute-audio-desc"
        />
        <div className="flex items-center gap-2">
          <VolumeX className="h-4 w-4 text-muted-foreground" />
          <Label
            htmlFor="mute-audio"
            className="text-sm font-medium cursor-pointer"
          >
            Remove Audio
          </Label>
        </div>
        <span id="mute-audio-desc" className="sr-only">
          Download video without audio
        </span>
      </div>

      <div className="flex items-center gap-3">
        <Label htmlFor="quality" className="text-sm text-muted-foreground whitespace-nowrap">
          Quality
        </Label>
        <Select value={isAudioOnly ? null : quality} onValueChange={onQualityChange} disabled={isAudioOnly}>
          <SelectTrigger
            disabled={isAudioOnly}
            id="quality"
            className="w-36 bg-secondary border-border"
            aria-label="Select video quality"
          >
            <SelectValue placeholder="Quality" />
          </SelectTrigger>
          <SelectContent>
            {qualities.map((q) => (
              <SelectItem key={q.value} value={q.value}>
                {q.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex items-center gap-3">
        <Label htmlFor="format" className="text-sm text-muted-foreground whitespace-nowrap">
          Format
        </Label>
        <Select value={format} onValueChange={onFormatChange}>
          <SelectTrigger
            id="format"
            className="w-28 bg-secondary border-border"
            aria-label="Select output format"
          >
            <SelectValue placeholder="Format" />
          </SelectTrigger>
          <SelectContent>
            {(isAudioOnly ? audioFormats : formats).map((f) => (
              <SelectItem key={f.value} value={f.value}>
                {f.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
};
