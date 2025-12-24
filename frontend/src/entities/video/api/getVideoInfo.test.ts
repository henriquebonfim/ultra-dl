import { beforeEach, describe, expect, it, mock } from 'bun:test';

// Store original fetch
const originalFetch = globalThis.fetch;

describe('getVideoInfo', () => {
  beforeEach(() => {
    // Reset fetch to original
    globalThis.fetch = originalFetch;
  });

  it('should construct correct request URL and body', async () => {
    let capturedUrl: string | undefined;
    let capturedOptions: RequestInit | undefined;

    globalThis.fetch = mock(async (url: string, options?: RequestInit) => {
      capturedUrl = url;
      capturedOptions = options;
      return {
        ok: true,
        json: async () => ({ meta: {}, formats: [] }),
      } as Response;
    }) as any;

    // Import dynamically to use mocked fetch
    const { getVideoInfo } = await import('./getVideoInfo');
    await getVideoInfo('http://youtube.com/watch?v=test');

    expect(capturedUrl).toContain('/api/v1/videos/resolutions');
    expect(capturedOptions?.method).toBe('POST');
    expect(capturedOptions?.headers).toEqual({ 'Content-Type': 'application/json' });
    expect(capturedOptions?.body).toBe(JSON.stringify({ url: 'http://youtube.com/watch?v=test' }));
  });

  it('should return parsed JSON on success', async () => {
    const mockData = {
      meta: { id: 'test', title: 'Test Video' },
      formats: [{ format_id: '22' }],
    };

    globalThis.fetch = mock(async () => ({
      ok: true,
      json: async () => mockData,
    })) as any;

    const { getVideoInfo } = await import('./getVideoInfo');
    const result = await getVideoInfo('http://youtube.com/watch?v=test');

    expect(result).toEqual(mockData);
  });

  it('should throw error on API failure', async () => {
    const errorData = { error: 'video_unavailable' };

    globalThis.fetch = mock(async () => ({
      ok: false,
      status: 400,
      json: async () => errorData,
    })) as any;

    const { getVideoInfo } = await import('./getVideoInfo');

    try {
      await getVideoInfo('invalid');
      expect(true).toBe(false); // Should not reach here
    } catch (error: any) {
      expect(error).toMatchObject(errorData);
    }
  });
});
