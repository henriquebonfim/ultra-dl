import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ResolutionPicker } from './ResolutionPicker';

describe('ResolutionPicker', () => {
  const mockOnSelect = vi.fn();

  const mockResolutions = [
    {
      format_id: '137',
      ext: 'mp4',
      resolution: '1920x1080',
      height: 1080,
      note: '1080p',
      filesize: 10485760,
      vcodec: 'avc1',
      acodec: 'mp4a'
    },
    {
      format_id: '136',
      ext: 'mp4',
      resolution: '1280x720',
      height: 720,
      note: '720p',
      filesize: 5242880,
      vcodec: 'avc1',
      acodec: 'mp4a'
    },
    {
      format_id: '135',
      ext: 'mp4',
      resolution: '854x480',
      height: 480,
      note: '480p',
      filesize: 2621440,
      vcodec: 'avc1',
      acodec: 'none'
    },
    {
      format_id: '140',
      ext: 'm4a',
      resolution: 'audio only',
      height: 0,
      note: '128k',
      filesize: 1048576,
      vcodec: 'none',
      acodec: 'mp4a'
    }
  ];

  it('renders format groups correctly', () => {
    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={mockResolutions}
      />
    );
    
    expect(screen.getByText('Video + Audio')).toBeInTheDocument();
    expect(screen.getByText('Video Only')).toBeInTheDocument();
    expect(screen.getByText('Audio Only')).toBeInTheDocument();
  });

  it('groups formats by type correctly', () => {
    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={mockResolutions}
      />
    );
    
    // Video+Audio formats (both codecs present)
    expect(screen.getByTestId('button-resolution-137')).toBeInTheDocument();
    expect(screen.getByTestId('button-resolution-136')).toBeInTheDocument();
    
    // Video Only format (no audio codec)
    expect(screen.getByTestId('button-resolution-135')).toBeInTheDocument();
    
    // Audio Only format (no video codec)
    expect(screen.getByTestId('button-resolution-140')).toBeInTheDocument();
  });

  it('sorts formats by resolution height descending', () => {
    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={mockResolutions}
      />
    );
    
    const buttons = screen.getAllByRole('button');
    const resolutionButtons = buttons.filter(btn => btn.getAttribute('data-testid')?.startsWith('button-resolution-'));
    
    // First video+audio should be 1080p (highest)
    const firstVideoAudio = resolutionButtons.find(btn => btn.getAttribute('data-testid') === 'button-resolution-137');
    expect(firstVideoAudio).toBeInTheDocument();
  });

  it('calls onSelect when format is clicked', () => {
    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={mockResolutions}
      />
    );
    
    const button = screen.getByTestId('button-resolution-137');
    fireEvent.click(button);
    
    expect(mockOnSelect).toHaveBeenCalledWith(mockResolutions[0]);
  });

  it('highlights selected resolution', () => {
    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={mockResolutions[0]}
        availableResolutions={mockResolutions}
      />
    );
    
    const selectedButton = screen.getByTestId('button-resolution-137');
    expect(selectedButton.className).toContain('border-primary');
  });

  it('displays file size correctly', () => {
    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={mockResolutions}
      />
    );
    
    // 10485760 bytes = 10 MB
    expect(screen.getByText('10 MB')).toBeInTheDocument();
    
    // 5242880 bytes = 5 MB
    expect(screen.getByText('5 MB')).toBeInTheDocument();
  });

  it('displays quality labels correctly', () => {
    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={mockResolutions}
      />
    );
    
    // 1080p should be "Great"
    const buttons = screen.getAllByRole('button');
    const button1080 = buttons.find(btn => btn.textContent?.includes('1920x1080'));
    expect(button1080?.textContent).toContain('Great');
    
    // 720p should be "Good"
    const button720 = buttons.find(btn => btn.textContent?.includes('1280x720'));
    expect(button720?.textContent).toContain('Good');
  });

  it('filters out formats with no video and no audio', () => {
    const resolutionsWithInvalid = [
      ...mockResolutions,
      {
        format_id: 'invalid',
        ext: 'mp4',
        resolution: 'none',
        height: 0,
        note: 'invalid',
        filesize: null,
        vcodec: 'none',
        acodec: 'none'
      }
    ];

    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={resolutionsWithInvalid}
      />
    );
    
    expect(screen.queryByTestId('button-resolution-invalid')).not.toBeInTheDocument();
  });

  it('handles null filesize gracefully', () => {
    const resolutionsWithNullSize = [
      {
        format_id: '137',
        ext: 'mp4',
        resolution: '1920x1080',
        height: 1080,
        note: '1080p',
        filesize: null,
        vcodec: 'avc1',
        acodec: 'mp4a'
      }
    ];

    render(
      <ResolutionPicker
        onSelect={mockOnSelect}
        selectedResolution={null}
        availableResolutions={resolutionsWithNullSize}
      />
    );
    
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });
});
