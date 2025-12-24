/**
 * Job entity types
 * Represents download job status and progress information
 */

export interface JobProgress {
  percentage: number;
  phase: string;
  speed?: string;
  eta?: number;
}

export interface Job {
  job_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: JobProgress | null;
  download_url?: string;
  error?: string;
  error_category?: string;
  expire_at?: string;
  time_remaining?: number;
}

export interface CreateJobRequest {
  url: string;
  formatId?: string;
  quality?: string;
  format?: string;
  muteAudio?: boolean;
  muteVideo?: boolean;
  startTime?: number;
  endTime?: number;
}

export interface CreateJobResponse {
  job_id: string;
  status: string;
}

export interface JobStatusResponse extends Job {}
