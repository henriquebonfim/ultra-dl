import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { UrlInput } from './UrlInput';

describe('UrlInput', () => {
  const mockOnSuccess = vi.fn();
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
    import.meta.env.VITE_API_URL = 'http://localhost:8000';
  });

  it('renders input field and check button', () => {
    render(<UrlInput onSuccess={mockOnSuccess} />);
    
    expect(screen.getByTestId('input-youtube-url')).toBeInTheDocument();
    expect(screen.getByTestId('button-check-video')).toBeInTheDocument();
  });

  it('validates empty URL', async () => {
    render(<UrlInput onSuccess={mockOnSuccess} />);
    
    const button = screen.getByTestId('button-check-video');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockOnSuccess).not.toHaveBeenCalled();
    });
  });

  it('validates invalid YouTube URL format', async () => {
    render(<UrlInput onSuccess={mockOnSuccess} />);
    
    const input = screen.getByTestId('input-youtube-url');
    fireEvent.change(input, { target: { value: 'https://example.com/video' } });
    
    const button = screen.getByTestId('button-check-video');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockOnSuccess).not.toHaveBeenCalled();
    });
  });

  it('accepts valid YouTube URL and calls API', async () => {
    const mockResponse = {
      meta: {
        id: 'test123',
        title: 'Test Video',
        uploader: 'Test Channel',
        duration: 120,
        thumbnail: 'https://example.com/thumb.jpg'
      },
      formats: [
        {
          format_id: '137',
          ext: 'mp4',
          resolution: '1920x1080',
          height: 1080,
          note: '1080p',
          filesize: 10485760,
          vcodec: 'avc1',
          acodec: 'mp4a'
        }
      ]
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    render(<UrlInput onSuccess={mockOnSuccess} />);
    
    const input = screen.getByTestId('input-youtube-url');
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=test123' } });
    
    const button = screen.getByTestId('button-check-video');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/videos/resolutions',
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=test123' })
        })
      );
      expect(mockOnSuccess).toHaveBeenCalledWith(mockResponse, 'https://www.youtube.com/watch?v=test123');
    });
  });

  it('handles API error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: async () => ({
        error: {
          code: 'VIDEO_UNAVAILABLE',
          message: 'This video is not available'
        }
      })
    });

    render(<UrlInput onSuccess={mockOnSuccess} />);
    
    const input = screen.getByTestId('input-youtube-url');
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=test123' } });
    
    const button = screen.getByTestId('button-check-video');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockOnSuccess).not.toHaveBeenCalled();
    });
  });

  it('shows loading state during API call', async () => {
    mockFetch.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(<UrlInput onSuccess={mockOnSuccess} />);
    
    const input = screen.getByTestId('input-youtube-url');
    fireEvent.change(input, { target: { value: 'https://www.youtube.com/watch?v=test123' } });
    
    const button = screen.getByTestId('button-check-video');
    fireEvent.click(button);
    
    expect(screen.getByText('Checking...')).toBeInTheDocument();
  });

  it('accepts youtu.be short URLs', async () => {
    const mockResponse = {
      meta: {
        id: 'test123',
        title: 'Test Video',
        uploader: 'Test Channel',
        duration: 120,
        thumbnail: 'https://example.com/thumb.jpg'
      },
      formats: []
    };

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => mockResponse
    });

    render(<UrlInput onSuccess={mockOnSuccess} />);
    
    const input = screen.getByTestId('input-youtube-url');
    fireEvent.change(input, { target: { value: 'https://youtu.be/test123' } });
    
    const button = screen.getByTestId('button-check-video');
    fireEvent.click(button);
    
    await waitFor(() => {
      expect(mockOnSuccess).toHaveBeenCalled();
    });
  });
});
