import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ProgressTracker } from './ProgressTracker';

describe('ProgressTracker', () => {
  const mockOnDownload = vi.fn();
  const mockOnDelete = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders pending state correctly', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="pending"
        progress={null}
      />
    );
    
    expect(screen.getByTestId('progress-tracker')).toBeInTheDocument();
    expect(screen.getByText('Preparing download...')).toBeInTheDocument();
    expect(screen.getByText('Your download will start shortly')).toBeInTheDocument();
  });

  it('shows cancel button in pending state when onDelete provided', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="pending"
        progress={null}
        onDelete={mockOnDelete}
      />
    );
    
    const cancelButton = screen.getByTestId('button-cancel-job');
    expect(cancelButton).toBeInTheDocument();
    
    fireEvent.click(cancelButton);
    expect(mockOnDelete).toHaveBeenCalled();
  });

  it('renders processing state with progress', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="processing"
        progress={{
          percentage: 45,
          phase: 'downloading',
          speed: '2.5 MB/s',
          eta: 30
        }}
      />
    );
    
    expect(screen.getByText('Downloading your video')).toBeInTheDocument();
    expect(screen.getByText('45%')).toBeInTheDocument();
    expect(screen.getByText('2.5 MB/s')).toBeInTheDocument();
    expect(screen.getByText(/ETA: 30s/)).toBeInTheDocument();
  });

  it('formats ETA correctly for minutes', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="processing"
        progress={{
          percentage: 25,
          phase: 'downloading',
          eta: 125
        }}
      />
    );
    
    expect(screen.getByText(/ETA: 2m 5s/)).toBeInTheDocument();
  });

  it('renders completed state with download button', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="completed"
        progress={null}
        downloadUrl="http://example.com/download/token123"
        onDownload={mockOnDownload}
      />
    );
    
    expect(screen.getByText('Download ready!')).toBeInTheDocument();
    expect(screen.getByText('Your video is ready to download')).toBeInTheDocument();
    
    const downloadButton = screen.getByTestId('button-download-file');
    expect(downloadButton).toBeInTheDocument();
    
    fireEvent.click(downloadButton);
    expect(mockOnDownload).toHaveBeenCalled();
  });

  it('shows delete button in completed state when onDelete provided', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="completed"
        progress={null}
        downloadUrl="http://example.com/download/token123"
        onDownload={mockOnDownload}
        onDelete={mockOnDelete}
      />
    );
    
    const deleteButton = screen.getByTestId('button-delete-job');
    expect(deleteButton).toBeInTheDocument();
    
    fireEvent.click(deleteButton);
    expect(mockOnDelete).toHaveBeenCalled();
  });

  it('renders failed state with error message', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="failed"
        progress={null}
        error="Video is unavailable"
      />
    );
    
    // ErrorCard shows generic error message, not the exact error text
    expect(screen.getByText(/System Error/)).toBeInTheDocument();
  });

  it('displays job ID', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="pending"
        progress={null}
      />
    );
    
    expect(screen.getByText(/Job ID: test-job-123/)).toBeInTheDocument();
  });

  it('shows websocket connection status', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="processing"
        progress={{
          percentage: 50,
          phase: 'downloading'
        }}
        connectionMethod="websocket"
        isWebSocketConnected={true}
      />
    );
    
    expect(screen.getByText('Real-time updates')).toBeInTheDocument();
  });

  it('shows polling status when websocket not connected', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="processing"
        progress={{
          percentage: 50,
          phase: 'downloading'
        }}
        connectionMethod="polling"
        isWebSocketConnected={false}
      />
    );
    
    expect(screen.getByText('Polling updates')).toBeInTheDocument();
  });

  it('displays expiration countdown in completed state', () => {
    const futureDate = new Date(Date.now() + 5 * 60 * 1000).toISOString(); // 5 minutes from now
    
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="completed"
        progress={null}
        downloadUrl="http://example.com/download/token123"
        expireAt={futureDate}
      />
    );
    
    // Use getAllByText since "Expires in:" appears twice in the component
    const expiresTexts = screen.getAllByText(/Expires in:/);
    expect(expiresTexts.length).toBeGreaterThan(0);
  });

  it('handles missing progress data gracefully', () => {
    render(
      <ProgressTracker
        jobId="test-job-123"
        status="processing"
        progress={{
          percentage: 30,
          phase: 'downloading'
        }}
      />
    );
    
    expect(screen.getByText('Calculating speed...')).toBeInTheDocument();
    expect(screen.getByText(/ETA: Calculating.../)).toBeInTheDocument();
  });
});
