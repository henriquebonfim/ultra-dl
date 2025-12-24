/**
 * API function to delete/cancel a job
 */

const API_URL = import.meta.env.VITE_API_URL;

export async function deleteJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_URL}/api/v1/jobs/${jobId}`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw { ...errorData, status: response.status };
  }
}
