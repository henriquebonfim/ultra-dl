import { useCallback, useEffect, useState, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { useToast } from "./use-toast";
import { io, Socket } from "socket.io-client";

interface JobProgress {
  percentage: number;
  phase: string;
  speed?: string;
  eta?: number;
}

interface JobStatusResponse {
  job_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  progress: JobProgress | null;
  download_url?: string;
  error?: string;
  error_category?: string;
  expire_at?: string;
  time_remaining?: number;
}

interface UseJobStatusWithWebSocketOptions {
  enabled?: boolean;
  preferWebSocket?: boolean;
}

/**
 * Enhanced job status hook with WebSocket support and automatic polling fallback.
 *
 * This hook attempts to use WebSocket for real-time updates, but automatically
 * falls back to HTTP polling if WebSocket connection fails or is unavailable.
 *
 * @param jobId - Job identifier to track
 * @param options - Configuration options
 * @returns Job status data and connection state
 */
export const useJobStatusWithWebSocket = (
  jobId: string | null,
  options: UseJobStatusWithWebSocketOptions = {}
) => {
  const { enabled = true, preferWebSocket = true } = options;
  const { toast } = useToast();

  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [usePolling, setUsePolling] = useState(!preferWebSocket);
  const [connectionMethod, setConnectionMethod] = useState<"websocket" | "polling" | "none">("none");
  const [wsConnected, setWsConnected] = useState(false);
  const [shouldStopPolling, setShouldStopPolling] = useState(false);
  
  const socketRef = useRef<Socket | null>(null);
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // Function to show error toasts based on error type
  const showErrorToast = useCallback((error: string, category?: string) => {
    let title = "Download Error";
    let description = error;
    const variant: "default" | "destructive" = "destructive";

    // Customize toast based on error category
    switch (category) {
      case "rate_limited":
        title = "Rate Limited";
        description = "You've made too many requests. Please wait a moment before trying again.";
        break;
      case "platform_rate_limited":
        title = "Platform Rate Limited";
        description = "YouTube is temporarily limiting requests. Please wait a few minutes before trying again.";
        break;
      case "geo_blocked":
        title = "Content Not Available";
        description = "This video is not available in your region. Try using a VPN or check YouTube directly.";
        break;
      case "login_required":
        title = "Login Required";
        description = "This video requires YouTube login. Please watch it directly on YouTube.";
        break;
      case "video_unavailable":
        title = "Video Unavailable";
        description = "This video is private, deleted, or unavailable for download.";
        break;
      case "network_error":
        title = "Connection Error";
        description = "Network issue detected. Check your connection and try again.";
        break;
      default:
        if (error.toLowerCase().includes("rate limited") || error.toLowerCase().includes("429")) {
          title = "Rate Limited";
          description = "Too many requests. Please wait before trying again.";
        }
    }

    toast({
      title,
      description,
      variant,
    });
  }, [toast]);

  // HTTP polling with React Query
  const pollingQuery = useQuery({
    queryKey: ["jobStatus", jobId],
    queryFn: async () => {
      if (!jobId) return null;
      
      const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch job status: ${response.statusText}`);
      }
      
      return response.json() as Promise<JobStatusResponse>;
    },
    enabled: enabled && usePolling && !!jobId && !shouldStopPolling,
    refetchInterval: (data) => {
      // Stop polling if job is completed or failed
      if (data?.status === "completed" || data?.status === "failed") {
        return false;
      }
      return 5000; // Poll every 5 seconds
    },
    staleTime: 0, // Always fetch fresh data
    gcTime: 0, // Don't cache completed jobs
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
  });

  // WebSocket connection management
  useEffect(() => {
    if (!enabled || !preferWebSocket || usePolling || !jobId) {
      return;
    }

    console.log("[JobStatus] Attempting WebSocket connection...");
    
    const socket = io(API_URL, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: 3,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      console.log("[JobStatus] WebSocket connected");
      setWsConnected(true);
      setConnectionMethod("websocket");
      
      // Subscribe to job updates
      socket.emit("subscribe_job", { job_id: jobId });
    });

    socket.on("disconnect", () => {
      console.log("[JobStatus] WebSocket disconnected");
      setWsConnected(false);
    });

    socket.on("connect_error", (error) => {
      console.error("[JobStatus] WebSocket connection error:", error);
      setWsConnected(false);
    });

    socket.on("job_progress", (data: { job_id: string; progress: JobProgress }) => {
      if (data.job_id === jobId) {
        setJobStatus((prev) => ({
          ...prev!,
          status: "processing",
          progress: data.progress,
        }));
      }
    });

    socket.on("job_completed", (data: { job_id: string; download_url: string; expire_at: string }) => {
      if (data.job_id === jobId) {
        setJobStatus((prev) => ({
          ...prev!,
          status: "completed",
          download_url: data.download_url,
          expire_at: data.expire_at,
        }));
      }
    });

    socket.on("job_failed", (data: { job_id: string; error: string; error_category?: string }) => {
      if (data.job_id === jobId) {
        setJobStatus((prev) => ({
          ...prev!,
          status: "failed",
          error: data.error,
          error_category: data.error_category,
        }));
        showErrorToast(data.error || "Download failed", data.error_category);
      }
    });

    return () => {
      if (socket) {
        socket.emit("unsubscribe_job", { job_id: jobId });
        socket.disconnect();
      }
    };
  }, [enabled, preferWebSocket, usePolling, jobId, API_URL, showErrorToast]);

  // Fallback to polling if WebSocket fails to connect within timeout
  useEffect(() => {
    if (!preferWebSocket || usePolling) {
      return;
    }

    // Give WebSocket 5 seconds to connect, then fallback to polling
    const fallbackTimer = setTimeout(() => {
      if (!wsConnected && !usePolling) {
        console.log("[JobStatus] WebSocket connection timeout, falling back to polling");
        setUsePolling(true);
        setConnectionMethod("polling");
        
        if (socketRef.current) {
          socketRef.current.disconnect();
        }
      }
    }, 5000);

    return () => clearTimeout(fallbackTimer);
  }, [preferWebSocket, wsConnected, usePolling]);

  // Sync polling data to local state when using polling
  useEffect(() => {
    if (usePolling && pollingQuery.data) {
      setJobStatus(pollingQuery.data);
    }
  }, [usePolling, pollingQuery.data]);

  // Handle polling errors with toast notifications
  useEffect(() => {
    if (pollingQuery.error && usePolling) {
      const error = pollingQuery.error as Error & { category?: string; error_category?: string };
      const errorMessage = error?.message || "Failed to check download status";
      const errorCategory = error?.category || error?.error_category;

      showErrorToast(errorMessage, errorCategory);
    }
  }, [pollingQuery.error, usePolling, showErrorToast]);

  // Initialize job status from polling on first load
  useEffect(() => {
    if (pollingQuery.data && !jobStatus) {
      setJobStatus(pollingQuery.data);
    }
  }, [pollingQuery.data, jobStatus]);

  // Function to manually disconnect WebSocket and stop polling
  const disconnect = useCallback(() => {
    console.log("[JobStatus] Manually disconnecting and stopping all updates");
    
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setWsConnected(false);
    }
    
    // Stop polling
    setShouldStopPolling(true);
    setConnectionMethod("none");
  }, []);

  return {
    data: jobStatus,
    error: pollingQuery.error,
    isLoading: pollingQuery.isLoading,
    connectionMethod,
    isWebSocketConnected: wsConnected,
    isPolling: usePolling,
    disconnect,
  };
};
