/**
 * API function to fetch video metadata and available formats
 */

import type { VideoMetadata } from '../model/types';

const API_URL = import.meta.env.VITE_API_URL;

export async function getVideoInfo(url: string): Promise<VideoMetadata> {
  const response = await fetch(`${API_URL}/api/v1/videos/resolutions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw { ...errorData, status: response.status };
  }

  const data: VideoMetadata = await response.json();
  return data;
}
