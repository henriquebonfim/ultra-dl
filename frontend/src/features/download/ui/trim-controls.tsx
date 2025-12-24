import { Button } from "@/shared/ui/button";
import { Input } from "@/shared/ui/input";
import { Label } from "@/shared/ui/label";
import { Pause, Play, Scissors } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

// CONSTANTS

const TRACK_PADDING = 8;
const HANDLE_SIZE_LARGE = 16;
const HANDLE_SIZE_SMALL = 12;
const INDICATOR_HEIGHT = 33;
const PLAYBACK_INTERVAL_MS = 1000;

// TYPES

interface TrimControlsProps {
  duration: number;
  startTime: number;
  endTime: number;
  isPlaying: boolean;
  onStartTimeChange: (time: number) => void;
  onEndTimeChange: (time: number) => void;
  onPlayPause: () => void;
  onCurrentTimeChange?: (time: number) => void;
  currentTime?: number;
}

type HandleType = 'start' | 'current' | 'end';

// UTILITY FUNCTIONS

/**
 * Formats seconds into HH:MM:SS format
 */
const formatTime = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours.toString().padStart(2, "0")}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
};

/**
 * Parses HH:MM:SS or MM:SS format string into seconds
 */
const parseTime = (timeStr: string): number => {
  const parts = timeStr.split(":");
  if (parts.length === 3) {
    const hours = parseInt(parts[0], 10) || 0;
    const mins = parseInt(parts[1], 10) || 0;
    const secs = parseInt(parts[2], 10) || 0;
    return hours * 3600 + mins * 60 + secs;
  } else if (parts.length === 2) {
    const mins = parseInt(parts[0], 10) || 0;
    const secs = parseInt(parts[1], 10) || 0;
    return mins * 60 + secs;
  }
  return 0;
};

/**
 * Safely calculates percentage, avoiding division by zero
 */
const calculatePercentage = (value: number, total: number): number => {
  return total > 0 ? (value / total) * 100 : 0;
};

/**
 * Clamps a value between min and max
 */
const clamp = (value: number, min: number, max: number): number => {
  return Math.max(min, Math.min(value, max));
};

// COMPONENT

export const TrimControls = ({
  duration,
  startTime,
  endTime,
  isPlaying,
  onStartTimeChange,
  onEndTimeChange,
  onPlayPause,
  onCurrentTimeChange,
  currentTime: externalCurrentTime,
}: TrimControlsProps) => {
  // STATE

  const [internalCurrentTime, setInternalCurrentTime] = useState(startTime);
  const [dragging, setDragging] = useState<HandleType | null>(null);

  // REFS

  const trackRef = useRef<HTMLDivElement>(null);
  const cachedRectRef = useRef<DOMRect | null>(null);

  // DERIVED STATE

  const currentTime = externalCurrentTime ?? internalCurrentTime;
  const clampedTime = clamp(currentTime, startTime, endTime);

  // MEMOIZED VALUES

  const positions = useMemo(() => ({
    start: calculatePercentage(startTime, duration),
    current: calculatePercentage(clampedTime, duration),
    end: calculatePercentage(endTime, duration),
  }), [duration, startTime, clampedTime, endTime]);

  // Sync internal state with external current time when not dragging
  useEffect(() => {
    if (externalCurrentTime !== undefined && !dragging) {
      setInternalCurrentTime(externalCurrentTime);
    }
  }, [externalCurrentTime, dragging]);

  // CALLBACKS

  const setCurrentTime = useCallback((time: number) => {
    setInternalCurrentTime(time);
    onCurrentTimeChange?.(time);
  }, [onCurrentTimeChange]);

  const getTimeFromPosition = useCallback((clientX: number): number => {
    if (!trackRef.current) return 0;
    const rect = trackRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const percentage = clamp(x / rect.width, 0, 1);
    return Math.round(percentage * duration);
  }, [duration]);



  const togglePlayback = useCallback(() => {
    if (currentTime >= endTime) {
      setCurrentTime(startTime);
    }
    onPlayPause();
  }, [currentTime, endTime, startTime, setCurrentTime, onPlayPause]);

  const handleStartTimeInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseTime(e.target.value);
    if (time >= 0 && time < endTime) {
      onStartTimeChange(time);
    }
  }, [endTime, onStartTimeChange]);

  const handleCurrentTimeInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseTime(e.target.value);
    if (time >= startTime && time <= endTime) {
      setCurrentTime(time);
    }
  }, [startTime, endTime, setCurrentTime]);

  const handleEndTimeInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseTime(e.target.value);
    if (time > startTime && time <= duration) {
      onEndTimeChange(time);
    }
  }, [startTime, duration, onEndTimeChange]);

  const handlePointerDown = useCallback((handle: HandleType) => (e: React.PointerEvent) => {
    e.preventDefault();

    if (trackRef.current) {
      cachedRectRef.current = trackRef.current.getBoundingClientRect();
    }

    setDragging(handle);
  }, [setDragging]);

  const handleTrackClick = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    const newTime = getTimeFromPosition(e.clientX);
    setCurrentTime(clamp(newTime, startTime, endTime));
  }, [getTimeFromPosition, setCurrentTime, startTime, endTime]);

  // Drag handling
  useEffect(() => {
    if (!dragging) return;

    const handlePointerMove = (e: PointerEvent) => {
      let newTime: number;
      if (cachedRectRef.current) {
        const x = e.clientX - cachedRectRef.current.left;
        const percentage = clamp(x / cachedRectRef.current.width, 0, 1);
        newTime = Math.round(percentage * duration);
      } else {
        newTime = getTimeFromPosition(e.clientX);
      }

      if (dragging === 'start') {
        onStartTimeChange(clamp(newTime, 0, endTime - 1));
      } else if (dragging === 'current') {
        setCurrentTime(clamp(newTime, startTime, endTime));
      } else if (dragging === 'end') {
        onEndTimeChange(clamp(newTime, startTime + 1, duration));
      }
    };

    const handlePointerUp = () => {
      setDragging(null);
      cachedRectRef.current = null;
    };

    document.addEventListener('pointermove', handlePointerMove);
    document.addEventListener('pointerup', handlePointerUp);

    return () => {
      document.removeEventListener('pointermove', handlePointerMove);
      document.removeEventListener('pointerup', handlePointerUp);
    };
  }, [dragging, duration, startTime, endTime, onStartTimeChange, onEndTimeChange, setCurrentTime, getTimeFromPosition, setDragging]);

  // RENDER

  return (
    <div className="w-full space-y-4" data-testid="trim-controls">
      <div className="flex items-center gap-2 text-sm font-medium text-foreground">
        <Scissors className="h-4 w-4 text-primary" />
        <span>Trim Video</span>
      </div>

      {/* Custom Triple-Handle Slider */}
      <div className="relative px-2 py-8" data-testid="slider-container">
        {/* Floating time indicator */}
        <div
          className="absolute top-2 z-30 pointer-events-none transition-all duration-100"
          style={{ left: `calc(${positions.current}% + ${TRACK_PADDING}px)` }}
          data-testid="time-indicator"
        >
          <div className="absolute left-1/2 -translate-x-1/2 bg-primary text-primary-foreground text-xs px-2 py-1 rounded-md whitespace-nowrap font-medium shadow-lg">
            {formatTime(clampedTime)}
          </div>
        </div>

        {/* Track container */}
        <div
          ref={trackRef}
          className="relative h-8 cursor-pointer touch-none"
          style={{ userSelect: 'none' }}
          onClick={handleTrackClick}
          data-testid="slider-track"
        >
          {/* Background track (full duration) */}
          <div className="absolute inset-x-0 top-1/2 h-2 -translate-y-1/2 bg-secondary rounded-full" />

          {/* Selected trim range */}
          <div
            className="absolute top-1/2 h-2 -translate-y-1/2 bg-gradient-to-r from-primary/80 to-primary rounded-full transition-all duration-100"
            style={{
              left: `${positions.start}%`,
              right: `${100 - positions.end}%`,
            }}
          />

          {/* Current time indicator line */}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-[0.5px] bg-white shadow-lg shadow-white/50 z-20 pointer-events-none transition-all duration-100"
            style={{ left: `${positions.current}%`, height: `${INDICATOR_HEIGHT}px` }}
          />

          {/* Start handle */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 bg-primary border-2 border-background rounded-full cursor-grab active:cursor-grabbing z-10 shadow-lg hover:scale-110 transition-transform touch-none"
            style={{ left: `${positions.start}%`, width: `${HANDLE_SIZE_LARGE}px`, height: `${HANDLE_SIZE_LARGE}px` }}
            onPointerDown={handlePointerDown('start')}
            aria-label="Start time"
            data-testid="start-handle"
          />

          {/* Current time handle */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 bg-white border-2 border-primary rounded-full cursor-grab active:cursor-grabbing z-20 shadow-lg hover:scale-110 transition-transform touch-none"
            style={{ left: `${positions.current}%`, width: `${HANDLE_SIZE_SMALL}px`, height: `${HANDLE_SIZE_SMALL}px` }}
            onPointerDown={handlePointerDown('current')}
            aria-label="Current time"
            data-testid="current-handle"
          />

          {/* End handle */}
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 bg-primary border-2 border-background rounded-full cursor-grab active:cursor-grabbing z-10 shadow-lg hover:scale-110 transition-transform touch-none"
            style={{ left: `${positions.end}%`, width: `${HANDLE_SIZE_LARGE}px`, height: `${HANDLE_SIZE_LARGE}px` }}
            onPointerDown={handlePointerDown('end')}
            aria-label="End time"
            data-testid="end-handle"
          />
        </div>
      </div>

      {/* Time Inputs and Controls */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Label htmlFor="start-time" className="text-sm text-muted-foreground whitespace-nowrap">
            Start
          </Label>
          <Input
            id="start-time"
            type="text"
            value={formatTime(startTime)}
            onChange={handleStartTimeInput}
            className="w-24 h-9 text-center bg-secondary border-border text-xs"
            aria-label="Start time"
            placeholder="00:00:00"
          />
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={togglePlayback}
            className="h-9 w-9"
            aria-label={isPlaying ? "Pause preview" : "Play preview"}
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </Button>

          <Input
            id="current-time"
            type="text"
            value={formatTime(clampedTime)}
            onChange={handleCurrentTimeInput}
            className="w-24 h-9 text-center bg-secondary border-border text-xs"
            aria-label="Current time"
            placeholder="00:00:00"
          />
        </div>

        <div className="flex items-center gap-2">
          <Input
            id="end-time"
            type="text"
            value={formatTime(endTime)}
            onChange={handleEndTimeInput}
            className="w-24 h-9 text-center bg-secondary border-border text-xs"
            aria-label="End time"
            placeholder="00:00:00"
          />
          <Label htmlFor="end-time" className="text-sm text-muted-foreground whitespace-nowrap">
            End
          </Label>
        </div>
      </div>
    </div>
  );
};
