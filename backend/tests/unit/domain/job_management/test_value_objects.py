"""
Unit tests for job management value objects.

Tests verify value object behavior including:
- Validation rules reject invalid inputs
- Immutability (cannot modify after creation)
- Equality and string representation

Requirements: 1.2, 1.4
"""

import pytest
from src.domain.job_management.value_objects import JobStatus, JobProgress


class TestJobStatus:
    """Test JobStatus enumeration."""
    
    def test_all_status_values_exist(self):
        """Test that all expected status values are defined."""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
    
    def test_is_terminal_returns_true_for_completed(self):
        """Test that COMPLETED status is terminal."""
        assert JobStatus.COMPLETED.is_terminal() is True
    
    def test_is_terminal_returns_true_for_failed(self):
        """Test that FAILED status is terminal."""
        assert JobStatus.FAILED.is_terminal() is True
    
    def test_is_terminal_returns_false_for_pending(self):
        """Test that PENDING status is not terminal."""
        assert JobStatus.PENDING.is_terminal() is False
    
    def test_is_terminal_returns_false_for_processing(self):
        """Test that PROCESSING status is not terminal."""
        assert JobStatus.PROCESSING.is_terminal() is False
    
    def test_is_active_returns_true_for_pending(self):
        """Test that PENDING status is active."""
        assert JobStatus.PENDING.is_active() is True
    
    def test_is_active_returns_true_for_processing(self):
        """Test that PROCESSING status is active."""
        assert JobStatus.PROCESSING.is_active() is True
    
    def test_is_active_returns_false_for_completed(self):
        """Test that COMPLETED status is not active."""
        assert JobStatus.COMPLETED.is_active() is False
    
    def test_is_active_returns_false_for_failed(self):
        """Test that FAILED status is not active."""
        assert JobStatus.FAILED.is_active() is False
    
    def test_equality(self):
        """Test that status values can be compared for equality."""
        status1 = JobStatus.PENDING
        status2 = JobStatus.PENDING
        status3 = JobStatus.PROCESSING
        
        assert status1 == status2
        assert status1 != status3
    
    def test_string_representation(self):
        """Test that status values have correct string representation."""
        assert str(JobStatus.PENDING.value) == "pending"
        assert str(JobStatus.PROCESSING.value) == "processing"
        assert str(JobStatus.COMPLETED.value) == "completed"
        assert str(JobStatus.FAILED.value) == "failed"


class TestJobProgress:
    """Test JobProgress value object."""
    
    def test_immutability_cannot_modify_percentage(self):
        """
        Test that JobProgress is immutable - cannot modify percentage.
        
        Verifies that attempting to modify attributes raises AttributeError.
        """
        progress = JobProgress(percentage=50, phase="downloading")
        
        with pytest.raises(AttributeError):
            progress.percentage = 75
    
    def test_immutability_cannot_modify_phase(self):
        """Test that JobProgress is immutable - cannot modify phase."""
        progress = JobProgress(percentage=50, phase="downloading")
        
        with pytest.raises(AttributeError):
            progress.phase = "completed"
    
    def test_immutability_cannot_modify_speed(self):
        """Test that JobProgress is immutable - cannot modify speed."""
        progress = JobProgress(percentage=50, phase="downloading", speed="1.5 MiB/s")
        
        with pytest.raises(AttributeError):
            progress.speed = "2.0 MiB/s"
    
    def test_immutability_cannot_modify_eta(self):
        """Test that JobProgress is immutable - cannot modify eta."""
        progress = JobProgress(percentage=50, phase="downloading", eta=60)
        
        with pytest.raises(AttributeError):
            progress.eta = 30
    
    def test_validation_rejects_negative_percentage(self):
        """Test that negative percentage values are rejected."""
        with pytest.raises(ValueError) as exc_info:
            JobProgress(percentage=-1, phase="downloading")
        assert "Percentage must be between 0 and 100" in str(exc_info.value)
    
    def test_validation_rejects_percentage_over_100(self):
        """Test that percentage values over 100 are rejected."""
        with pytest.raises(ValueError) as exc_info:
            JobProgress(percentage=101, phase="downloading")
        assert "Percentage must be between 0 and 100" in str(exc_info.value)
    
    def test_validation_rejects_empty_phase(self):
        """Test that empty phase string is rejected."""
        with pytest.raises(ValueError) as exc_info:
            JobProgress(percentage=50, phase="")
        assert "Phase is required" in str(exc_info.value)
    
    def test_validation_accepts_valid_percentage_0(self):
        """Test that percentage 0 is valid."""
        progress = JobProgress(percentage=0, phase="initializing")
        assert progress.percentage == 0
    
    def test_validation_accepts_valid_percentage_100(self):
        """Test that percentage 100 is valid."""
        progress = JobProgress(percentage=100, phase="completed")
        assert progress.percentage == 100
    
    def test_equality_same_values(self):
        """Test that progress objects with same values are equal."""
        progress1 = JobProgress(percentage=50, phase="downloading", speed="1.5 MiB/s", eta=60)
        progress2 = JobProgress(percentage=50, phase="downloading", speed="1.5 MiB/s", eta=60)
        
        assert progress1 == progress2
    
    def test_equality_different_percentage(self):
        """Test that progress objects with different percentages are not equal."""
        progress1 = JobProgress(percentage=50, phase="downloading")
        progress2 = JobProgress(percentage=75, phase="downloading")
        
        assert progress1 != progress2
    
    def test_equality_different_phase(self):
        """Test that progress objects with different phases are not equal."""
        progress1 = JobProgress(percentage=50, phase="downloading")
        progress2 = JobProgress(percentage=50, phase="processing")
        
        assert progress1 != progress2
    
    def test_to_dict_serialization(self):
        """Test that to_dict() correctly serializes progress."""
        progress = JobProgress(percentage=50, phase="downloading", speed="1.5 MiB/s", eta=60)
        data = progress.to_dict()
        
        assert data["percentage"] == 50
        assert data["phase"] == "downloading"
        assert data["speed"] == "1.5 MiB/s"
        assert data["eta"] == 60
    
    def test_to_dict_handles_optional_fields(self):
        """Test that to_dict() handles missing optional fields."""
        progress = JobProgress(percentage=50, phase="downloading")
        data = progress.to_dict()
        
        assert data["percentage"] == 50
        assert data["phase"] == "downloading"
        assert data["speed"] is None
        assert data["eta"] is None
    
    def test_from_dict_deserialization(self):
        """Test that from_dict() correctly deserializes progress."""
        data = {
            "percentage": 50,
            "phase": "downloading",
            "speed": "1.5 MiB/s",
            "eta": 60
        }
        progress = JobProgress.from_dict(data)
        
        assert progress.percentage == 50
        assert progress.phase == "downloading"
        assert progress.speed == "1.5 MiB/s"
        assert progress.eta == 60
    
    def test_from_dict_handles_missing_optional_fields(self):
        """Test that from_dict() handles missing optional fields."""
        data = {
            "percentage": 50,
            "phase": "downloading"
        }
        progress = JobProgress.from_dict(data)
        
        assert progress.percentage == 50
        assert progress.phase == "downloading"
        assert progress.speed is None
        assert progress.eta is None
    
    def test_from_dict_uses_defaults_for_missing_required_fields(self):
        """Test that from_dict() uses defaults when required fields are missing."""
        data = {}
        progress = JobProgress.from_dict(data)
        
        assert progress.percentage == 0
        assert progress.phase == "initializing"
    
    def test_initial_factory_method(self):
        """Test that initial() creates correct initial progress."""
        progress = JobProgress.initial()
        
        assert progress.percentage == 0
        assert progress.phase == "initializing"
        assert progress.speed is None
        assert progress.eta is None
    
    def test_metadata_extraction_factory_method(self):
        """Test that metadata_extraction() creates correct progress."""
        progress = JobProgress.metadata_extraction()
        
        assert progress.percentage == 5
        assert progress.phase == "extracting metadata"
        assert progress.speed is None
        assert progress.eta is None
    
    def test_downloading_factory_method(self):
        """Test that downloading() creates correct progress."""
        progress = JobProgress.downloading(percentage=50, speed="1.5 MiB/s", eta=60)
        
        assert progress.percentage == 50
        assert progress.phase == "downloading"
        assert progress.speed == "1.5 MiB/s"
        assert progress.eta == 60
    
    def test_downloading_factory_method_with_defaults(self):
        """Test that downloading() works with minimal parameters."""
        progress = JobProgress.downloading(percentage=50)
        
        assert progress.percentage == 50
        assert progress.phase == "downloading"
        assert progress.speed is None
        assert progress.eta is None
    
    def test_processing_factory_method(self):
        """Test that processing() creates correct progress."""
        progress = JobProgress.processing(percentage=90)
        
        assert progress.percentage == 90
        assert progress.phase == "processing"
        assert progress.speed is None
        assert progress.eta is None
    
    def test_processing_factory_method_with_default_percentage(self):
        """Test that processing() uses default percentage."""
        progress = JobProgress.processing()
        
        assert progress.percentage == 90
        assert progress.phase == "processing"
    
    def test_completed_factory_method(self):
        """Test that completed() creates correct progress."""
        progress = JobProgress.completed()
        
        assert progress.percentage == 100
        assert progress.phase == "completed"
        assert progress.speed is None
        assert progress.eta is None
