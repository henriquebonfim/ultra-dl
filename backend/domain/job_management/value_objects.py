"""
Job Management Value Objects

Immutable value objects for job status and progress tracking.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class JobStatus(Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    
    def is_terminal(self) -> bool:
        """Check if status is terminal (completed or failed)."""
        return self in (JobStatus.COMPLETED, JobStatus.FAILED)
    
    def is_active(self) -> bool:
        """Check if job is actively processing."""
        return self in (JobStatus.PENDING, JobStatus.PROCESSING)


@dataclass(frozen=True)
class JobProgress:
    """
    Value object representing job progress information.
    
    Immutable to ensure thread-safety when passed between components.
    """
    percentage: int
    phase: str
    speed: Optional[str] = None
    eta: Optional[int] = None  # Estimated time remaining in seconds
    
    def __post_init__(self):
        """Validate progress values."""
        if not 0 <= self.percentage <= 100:
            raise ValueError(f"Percentage must be between 0 and 100, got {self.percentage}")
        if not self.phase:
            raise ValueError("Phase is required")
    
    def to_dict(self):
        """Convert to dictionary for serialization."""
        return {
            "percentage": self.percentage,
            "phase": self.phase,
            "speed": self.speed,
            "eta": self.eta
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'JobProgress':
        """Create JobProgress from dictionary."""
        return cls(
            percentage=data.get("percentage", 0),
            phase=data.get("phase", "initializing"),
            speed=data.get("speed"),
            eta=data.get("eta")
        )
    
    @classmethod
    def initial(cls) -> 'JobProgress':
        """Create initial progress state."""
        return cls(percentage=0, phase="initializing")
    
    @classmethod
    def metadata_extraction(cls) -> 'JobProgress':
        """Create progress for metadata extraction phase."""
        return cls(percentage=5, phase="extracting metadata")
    
    @classmethod
    def downloading(cls, percentage: int, speed: Optional[str] = None, eta: Optional[int] = None) -> 'JobProgress':
        """Create progress for downloading phase."""
        return cls(percentage=percentage, phase="downloading", speed=speed, eta=eta)
    
    @classmethod
    def processing(cls, percentage: int = 90) -> 'JobProgress':
        """Create progress for post-processing phase."""
        return cls(percentage=percentage, phase="processing")
    
    @classmethod
    def completed(cls) -> 'JobProgress':
        """Create progress for completed state."""
        return cls(percentage=100, phase="completed")
