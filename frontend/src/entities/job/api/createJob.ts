/**
 * API function to create a download job
 */

import type { CreateJobRequest, CreateJobResponse } from '../model/types';

const API_URL = import.meta.env.VITE_API_URL;

export async function createJob(request: CreateJobRequest): Promise<CreateJobResponse> {
  const payload = {
    url: request.url,
    format_id: request.formatId,
    quality: request.quality,
    format: request.format,
    mute_audio: request.muteAudio,
    mute_video: request.muteVideo,
    start_time: request.startTime,
    end_time: request.endTime,
  };

  const response = await fetch(`${API_URL}/api/v1/downloads/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw { ...errorData, status: response.status };
  }

  const data: CreateJobResponse = await response.json();
  return data;
}
