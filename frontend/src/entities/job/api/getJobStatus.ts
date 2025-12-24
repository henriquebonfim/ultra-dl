/**
 * API function to fetch job status
 */

import type { Job } from '../model/types';

const API_URL = import.meta.env.VITE_API_URL;

export async function getJobStatus(jobId: string): Promise<Job> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}`);

  if (!response.ok) {
    const errorData = await response.json();
    throw { ...errorData, status: response.status };
  }

  const data: Job = await response.json();
  return data;
}
