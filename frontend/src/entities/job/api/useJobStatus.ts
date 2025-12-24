import { formatErrorForToast, parseApiError } from "@/shared/lib/errors";
import { useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { io, Socket } from "socket.io-client";
import { toast } from "sonner";
import type { JobProgress, JobStatusResponse } from "../model/types";

interface UseJobStatusWithWebSocketOptions {
  enabled?: boolean;
  preferWebSocket?: boolean;
}

export const useJobStatus = (
  jobId: string | null,
  options: UseJobStatusWithWebSocketOptions = {}
) => {
  const { enabled = true, preferWebSocket = true } = options;

  const [jobStatus, setJobStatus] = useState<JobStatusResponse | null>(null);
  const [usePolling, setUsePolling] = useState(!preferWebSocket);
  const [connectionMethod, setConnectionMethod] = useState<"websocket" | "polling" | "none">("none");
  const [wsConnected, setWsConnected] = useState(false);
  const [shouldStopPolling, setShouldStopPolling] = useState(false);

  const socketRef = useRef<Socket | null>(null);
  const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  // Function to show error toasts based on error type
  const showErrorToast = useCallback((error: unknown) => {
    const errorInfo = parseApiError(error);
    toast.error(formatErrorForToast(errorInfo));
  }, []);

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
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === "completed" || data?.status === "failed") {
        return false;
      }
      return 5000;
    },
    staleTime: 0,
    gcTime: 0,
    retry: 3,
  });

  // WebSocket connection management
  useEffect(() => {
    if (!enabled || !preferWebSocket || usePolling || !jobId) {
      return;
    }

    const socket = io(API_URL, {
      transports: ["websocket", "polling"],
      reconnection: true,
      reconnectionAttempts: 3,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on("connect", () => {
      setWsConnected(true);
      setConnectionMethod("websocket");
      socket.emit("subscribe_job", { job_id: jobId });
    });

    socket.on("disconnect", () => {
      setWsConnected(false);
    });

    socket.on("connect_error", () => {
      setWsConnected(false);
    });

    socket.on("job_progress", (data: { job_id: string; progress: JobProgress }) => {
      if (data.job_id === jobId) {
        setJobStatus((prev) => ({
          ...(prev as JobStatusResponse),
          job_id: jobId,
          status: "processing",
          progress: data.progress,
        }));
      }
    });

    socket.on("job_completed", (data: { job_id: string; download_url: string; expire_at: string }) => {
      if (data.job_id === jobId) {
        setJobStatus((prev) => ({
          ...(prev as JobStatusResponse),
          job_id: jobId,
          status: "completed",
          download_url: data.download_url,
          expire_at: data.expire_at,
        }));
        disconnect(); // Explicitly disconnect socket on completion
      }
    });

    socket.on("job_failed", (data: { job_id: string; error: string; error_category?: string }) => {
      if (data.job_id === jobId) {
        setJobStatus((prev) => ({
          ...(prev as JobStatusResponse),
          job_id: jobId,
          status: "failed",
          error: data.error,
          error_category: data.error_category,
        }));
        showErrorToast({ message: data.error, error: data.error_category || "download_failed" });
        setShouldStopPolling(true);
        socket.disconnect(); // Disconnect on failure
      }
    });

    socket.on("job_warning", (data: { job_id: string; message: string }) => {
      if (data.job_id === jobId) {
         toast.warning("Network Warning", {
           description: data.message,
           duration: 5000,
         });
      }
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, [enabled, preferWebSocket, usePolling, jobId, API_URL, showErrorToast]);

  // Fallback to polling
  useEffect(() => {
    if (!preferWebSocket || usePolling) {
      return;
    }

    const fallbackTimer = setTimeout(() => {
      if (!wsConnected && !usePolling) {
        setUsePolling(true);
        setConnectionMethod("polling");
        if (socketRef.current) {
          socketRef.current.disconnect();
        }
      }
    }, 5000);

    return () => clearTimeout(fallbackTimer);
  }, [preferWebSocket, wsConnected, usePolling]);

  // Sync polling data
  useEffect(() => {
    if (usePolling && pollingQuery.data) {
      setJobStatus(pollingQuery.data);
    }
  }, [usePolling, pollingQuery.data]);

  const disconnect = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
      setWsConnected(false);
    }
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
