"""
Hypothesis Strategies for Property-Based Testing

Custom strategies for generating domain objects and test data.
Used by property-based tests to verify universal properties.

Requirements: 6.1, 6.2, 6.3, 6.4
"""

import string
from datetime import datetime, timedelta
from typing import Optional

from hypothesis import strategies as st
from hypothesis.strategies import SearchStrategy

from src.domain.job_management.value_objects import JobStatus, JobProgress
from src.domain.video_processing.value_objects import FormatId
from src.domain.file_storage.value_objects import DownloadToken


# =============================================================================
# Primitive Strategies
# =============================================================================

@st.composite
def youtube_video_ids(draw) -> str:
    """Generate valid YouTube video IDs (11 characters, alphanumeric + - and _)."""
    chars = string.ascii_letters + string.digits + "-_"
    return draw(st.text(alphabet=chars, min_size=11, max_size=11))


@st.composite
def valid_youtube_urls(draw) -> str:
    """Generate valid YouTube URLs."""
    video_id = draw(youtube_video_ids())
    domain_choice = draw(st.sampled_from([
        "https://www.youtube.com/watch?v=",
        "https://youtube.com/watch?v=",
        "https://youtu.be/",
        "https://m.youtube.com/watch?v=",
    ]))
    return domain_choice + video_id


@st.composite
def invalid_youtube_urls(draw) -> str:
    """Generate invalid YouTube URLs for error testing."""
    variant = draw(st.sampled_from([
        "non_youtube",
        "malformed",
        "missing_video_id",
        "empty",
    ]))
    
    if variant == "non_youtube":
        return draw(st.sampled_from([
            "https://vimeo.com/123456789",
            "https://dailymotion.com/video/x123456",
            "https://example.com/video",
        ]))
    elif variant == "malformed":
        return draw(st.text(min_size=1, max_size=50).filter(
            lambda x: "youtube" not in x.lower()
        ))
    elif variant == "missing_video_id":
        return draw(st.sampled_from([
            "https://www.youtube.com/watch",
            "https://www.youtube.com/",
            "https://youtu.be/",
        ]))
    else:  # empty
        return ""


@st.composite
def valid_format_ids(draw) -> str:
    """Generate valid yt-dlp format IDs."""
    format_type = draw(st.sampled_from(["keyword", "numeric", "combined"]))
    
    keywords = ["best", "worst", "bestaudio", "bestvideo", "worstaudio", "worstvideo"]
    
    if format_type == "keyword":
        return draw(st.sampled_from(keywords))
    elif format_type == "numeric":
        return str(draw(st.integers(min_value=1, max_value=999)))
    else:  # combined
        first = draw(st.sampled_from(keywords + [str(i) for i in range(137, 251)]))
        second = draw(st.sampled_from(keywords + [str(i) for i in range(137, 251)]))
        return f"{first}+{second}"


@st.composite
def invalid_format_ids(draw) -> str:
    """Generate invalid format IDs for error testing."""
    return draw(st.sampled_from([
        "",
        "invalid_format",
        "best@video",
        "format with spaces",
        "!@#$%",
    ]))


@st.composite
def valid_token_strings(draw, min_length: int = 32) -> str:
    """Generate valid download token strings."""
    chars = string.ascii_letters + string.digits + "-_"
    length = draw(st.integers(min_value=min_length, max_value=64))
    return draw(st.text(alphabet=chars, min_size=length, max_size=length))


@st.composite
def invalid_token_strings(draw) -> str:
    """Generate invalid token strings for error testing."""
    variant = draw(st.sampled_from(["too_short", "empty", "special_chars"]))
    
    if variant == "too_short":
        return draw(st.text(min_size=1, max_size=31))
    elif variant == "empty":
        return ""
    else:  # special_chars
        return "token!@#$%^&*()" + "a" * 20


# =============================================================================
# Value Object Strategies
# =============================================================================

def job_statuses() -> SearchStrategy[JobStatus]:
    """Generate random JobStatus values."""
    return st.sampled_from(list(JobStatus))


def terminal_job_statuses() -> SearchStrategy[JobStatus]:
    """Generate only terminal job statuses (COMPLETED or FAILED)."""
    return st.sampled_from([JobStatus.COMPLETED, JobStatus.FAILED])


def active_job_statuses() -> SearchStrategy[JobStatus]:
    """Generate only active job statuses (PENDING or PROCESSING)."""
    return st.sampled_from([JobStatus.PENDING, JobStatus.PROCESSING])


@st.composite
def job_progress_values(draw) -> JobProgress:
    """Generate random JobProgress values."""
    percentage = draw(st.integers(min_value=0, max_value=100))
    phase = draw(st.sampled_from([
        "initializing",
        "extracting metadata",
        "downloading",
        "processing",
        "completed",
    ]))
    speed = draw(st.one_of(
        st.none(),
        st.sampled_from(["1.5 MiB/s", "500 KiB/s", "10 MiB/s"]),
    ))
    eta = draw(st.one_of(
        st.none(),
        st.integers(min_value=0, max_value=3600),
    ))
    
    return JobProgress(percentage=percentage, phase=phase, speed=speed, eta=eta)


@st.composite
def format_id_objects(draw) -> FormatId:
    """Generate FormatId value objects."""
    format_str = draw(valid_format_ids())
    return FormatId(format_str)


@st.composite
def download_token_objects(draw) -> DownloadToken:
    """Generate DownloadToken value objects."""
    token_str = draw(valid_token_strings())
    return DownloadToken(token_str)


def job_ids() -> SearchStrategy[str]:
    """Generate UUID-like job IDs."""
    return st.uuids().map(str)


# =============================================================================
# Entity Strategies
# =============================================================================


@st.composite
def datetimes_in_past(draw, max_days_ago: int = 30) -> datetime:
    """Generate datetime values in the past."""
    days_ago = draw(st.integers(min_value=0, max_value=max_days_ago))
    hours_ago = draw(st.integers(min_value=0, max_value=23))
    return datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)


@st.composite
def datetimes_in_future(draw, max_days_ahead: int = 7) -> datetime:
    """Generate datetime values in the future."""
    days_ahead = draw(st.integers(min_value=0, max_value=max_days_ahead))
    hours_ahead = draw(st.integers(min_value=0, max_value=23))
    return datetime.utcnow() + timedelta(days=days_ahead, hours=hours_ahead)


# =============================================================================
# State Transition Strategies
# =============================================================================

@st.composite
def valid_state_transitions(draw) -> list:
    """
    Generate valid sequences of job state transitions.
    
    Valid transitions:
    - PENDING -> PROCESSING (via start())
    - PROCESSING -> COMPLETED (via complete())
    - PROCESSING -> FAILED (via fail())
    - Any state -> FAILED (via fail())
    """
    transitions = []
    current_state = JobStatus.PENDING
    
    # Always start with 'start' to move from PENDING to PROCESSING
    transitions.append("start")
    current_state = JobStatus.PROCESSING
    
    # Optionally add progress updates
    num_progress_updates = draw(st.integers(min_value=0, max_value=5))
    for _ in range(num_progress_updates):
        transitions.append("update_progress")
    
    # End with either complete or fail
    final_transition = draw(st.sampled_from(["complete", "fail"]))
    transitions.append(final_transition)
    
    return transitions


@st.composite
def invalid_state_transitions(draw) -> tuple:
    """
    Generate invalid state transition attempts.
    
    Returns tuple of (current_state, attempted_transition).
    """
    invalid_combos = [
        (JobStatus.COMPLETED, "start"),
        (JobStatus.COMPLETED, "complete"),
        (JobStatus.COMPLETED, "update_progress"),
        (JobStatus.FAILED, "start"),
        (JobStatus.FAILED, "complete"),
        (JobStatus.FAILED, "update_progress"),
        (JobStatus.PENDING, "complete"),
        (JobStatus.PENDING, "update_progress"),
    ]
    return draw(st.sampled_from(invalid_combos))


# =============================================================================
# IP Address Strategies (for rate limiting tests)
# =============================================================================

@st.composite
def ipv4_addresses(draw) -> str:
    """Generate valid IPv4 addresses."""
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(4)]
    return ".".join(str(o) for o in octets)


@st.composite
def ipv6_addresses(draw) -> str:
    """Generate valid IPv6 addresses."""
    groups = [draw(st.integers(min_value=0, max_value=65535)) for _ in range(8)]
    return ":".join(f"{g:04x}" for g in groups)


@st.composite
def ip_addresses(draw) -> str:
    """Generate either IPv4 or IPv6 addresses."""
    return draw(st.one_of(ipv4_addresses(), ipv6_addresses()))
