import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorCard } from './ErrorCard';
import { ErrorInfo } from '@/lib/errors';

describe('ErrorCard', () => {
  const mockError: ErrorInfo = {
    title: 'Video Unavailable',
    message: 'This video is not available for download',
    action: 'Please check if the video is public and try again',
    category: 'VIDEO_UNAVAILABLE'
  };

  const mockOnRetry = vi.fn();
  const mockOnDismiss = vi.fn();

  it('renders error information in alert variant', () => {
    render(
      <ErrorCard
        error={mockError}
        variant="alert"
      />
    );
    
    expect(screen.getByText('Video Unavailable')).toBeInTheDocument();
    expect(screen.getByText('This video is not available for download')).toBeInTheDocument();
    expect(screen.getByText('Please check if the video is public and try again')).toBeInTheDocument();
  });

  it('renders error information in card variant', () => {
    render(
      <ErrorCard
        error={mockError}
        variant="card"
      />
    );
    
    expect(screen.getByText('Video Unavailable')).toBeInTheDocument();
    expect(screen.getByText('This video is not available for download')).toBeInTheDocument();
    expect(screen.getByText('Please check if the video is public and try again')).toBeInTheDocument();
  });

  it('shows retry button when onRetry provided and showRetry is true', () => {
    render(
      <ErrorCard
        error={mockError}
        onRetry={mockOnRetry}
        variant="alert"
        showRetry={true}
      />
    );
    
    const retryButton = screen.getByText('Try Again');
    expect(retryButton).toBeInTheDocument();
    
    fireEvent.click(retryButton);
    expect(mockOnRetry).toHaveBeenCalled();
  });

  it('hides retry button when showRetry is false', () => {
    render(
      <ErrorCard
        error={mockError}
        onRetry={mockOnRetry}
        variant="alert"
        showRetry={false}
      />
    );
    
    expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
  });

  it('shows dismiss button when onDismiss provided', () => {
    render(
      <ErrorCard
        error={mockError}
        onDismiss={mockOnDismiss}
        variant="alert"
      />
    );
    
    const dismissButton = screen.getByText('Dismiss');
    expect(dismissButton).toBeInTheDocument();
    
    fireEvent.click(dismissButton);
    expect(mockOnDismiss).toHaveBeenCalled();
  });

  it('renders different error categories correctly', () => {
    const networkError: ErrorInfo = {
      title: 'Network Error',
      message: 'Unable to connect to the server',
      action: 'Check your internet connection and try again',
      category: 'NETWORK_ERROR'
    };

    render(
      <ErrorCard
        error={networkError}
        variant="alert"
      />
    );
    
    expect(screen.getByText('Network Error')).toBeInTheDocument();
    expect(screen.getByText('Unable to connect to the server')).toBeInTheDocument();
  });

  it('displays actionable guidance prominently', () => {
    render(
      <ErrorCard
        error={mockError}
        variant="alert"
      />
    );
    
    const actionText = screen.getByText('Please check if the video is public and try again');
    expect(actionText).toBeInTheDocument();
  });

  it('works without retry or dismiss buttons', () => {
    render(
      <ErrorCard
        error={mockError}
        variant="alert"
      />
    );
    
    expect(screen.queryByText('Try Again')).not.toBeInTheDocument();
    expect(screen.queryByText('Dismiss')).not.toBeInTheDocument();
  });

  it('renders both retry and dismiss buttons when both provided', () => {
    render(
      <ErrorCard
        error={mockError}
        onRetry={mockOnRetry}
        onDismiss={mockOnDismiss}
        variant="card"
        showRetry={true}
      />
    );
    
    expect(screen.getByText('Try Again')).toBeInTheDocument();
    expect(screen.getByText('Dismiss')).toBeInTheDocument();
  });
});
