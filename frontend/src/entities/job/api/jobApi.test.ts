import { beforeEach, describe, expect, it, mock } from 'bun:test';

// Store original fetch
const originalFetch = globalThis.fetch;

describe('Job API', () => {
  beforeEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('createJob', () => {
    it('should construct correct request', async () => {
      let capturedUrl: string | undefined;
      let capturedOptions: RequestInit | undefined;

      globalThis.fetch = mock(async (url: string, options?: RequestInit) => {
        capturedUrl = url;
        capturedOptions = options;
        return {
          ok: true,
          json: async () => ({ job_id: '123', status: 'pending' }),
        } as Response;
      }) as any;

      const { createJob } = await import('./createJob');
      const result = await createJob({
        url: 'http://test.com',
        formatId: 'mp4',
        quality: '1080',
        format: 'mp4',
        muteAudio: false,
        muteVideo: false,
      });

      expect(capturedUrl).toContain('/api/v1/downloads/');
      expect(capturedOptions?.method).toBe('POST');
      expect(result).toEqual({ job_id: '123', status: 'pending' });
    });

    it('should throw error on failure', async () => {
      const errorData = { error: 'failed' };

      globalThis.fetch = mock(async () => ({
        ok: false,
        status: 500,
        json: async () => errorData,
      })) as any;

      const { createJob } = await import('./createJob');

      try {
        await createJob({ url: '', formatId: '' });
        expect(true).toBe(false);
      } catch (error: any) {
        expect(error).toMatchObject(errorData);
      }
    });
  });

  describe('deleteJob', () => {
    it('should call DELETE endpoint', async () => {
      let capturedUrl: string | undefined;
      let capturedMethod: string | undefined;

      globalThis.fetch = mock(async (url: string, options?: RequestInit) => {
        capturedUrl = url;
        capturedMethod = options?.method;
        return { ok: true } as Response;
      }) as any;

      const { deleteJob } = await import('./deleteJob');
      await deleteJob('123');

      expect(capturedUrl).toContain('/api/v1/jobs/123');
      expect(capturedMethod).toBe('DELETE');
    });

    it('should throw error on failure', async () => {
      const errorData = { error: 'not_found' };

      globalThis.fetch = mock(async () => ({
        ok: false,
        status: 404,
        json: async () => errorData,
      })) as any;

      const { deleteJob } = await import('./deleteJob');

      try {
        await deleteJob('123');
        expect(true).toBe(false);
      } catch (error: any) {
        expect(error).toMatchObject(errorData);
      }
    });
  });

  describe('getJobStatus', () => {
    it('should fetch job status', async () => {
      const mockResponse = { job_id: '123', status: 'processing', progress: null };

      globalThis.fetch = mock(async () => ({
        ok: true,
        json: async () => mockResponse,
      })) as any;

      const { getJobStatus } = await import('./getJobStatus');
      const result = await getJobStatus('123');

      expect(result).toEqual(mockResponse);
    });

    it('should throw error on failure', async () => {
      const errorData = { error: 'not_found' };

      globalThis.fetch = mock(async () => ({
        ok: false,
        status: 404,
        json: async () => errorData,
      })) as any;

      const { getJobStatus } = await import('./getJobStatus');

      try {
        await getJobStatus('123');
        expect(true).toBe(false);
      } catch (error: any) {
        expect(error).toMatchObject(errorData);
      }
    });
  });
});
