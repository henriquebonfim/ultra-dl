"""
Unit Tests for Event Publisher

Tests the EventPublisher application service for domain event dispatching.
Requirements: 9.4
"""

import threading
import time
from datetime import datetime, timedelta
from typing import List

from application.event_publisher import EventPublisher
from domain.events import (
    DomainEvent,
    JobStartedEvent,
    JobCompletedEvent,
    JobFailedEvent,
    JobProgressUpdatedEvent
)
from domain.job_management.value_objects import JobProgress


def test_subscribe_registers_handlers():
    """
    Test that subscribe registers handlers for event types.
    
    Verifies that handlers are properly registered and can be retrieved
    for the correct event type.
    """
    print("\n=== Testing Subscribe Registers Handlers ===")
    
    publisher = EventPublisher()
    call_count = [0]
    
    def handler(event: DomainEvent):
        call_count[0] += 1
    
    # Subscribe handler
    publisher.subscribe(JobStartedEvent, handler)
    
    # Verify handler is registered by publishing an event
    event = JobStartedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        url="https://youtube.com/watch?v=test",
        format_id="137+140"
    )
    
    publisher.publish(event)
    
    assert call_count[0] == 1, f"Expected handler to be called once, got {call_count[0]}"
    
    print("✓ Handler registered and called successfully")
    return True


def test_subscribe_multiple_handlers():
    """
    Test that multiple handlers can be registered for the same event type.
    
    Verifies that all registered handlers are called when an event is published.
    """
    print("\n=== Testing Multiple Handlers for Same Event ===")
    
    publisher = EventPublisher()
    call_counts = {"handler1": 0, "handler2": 0, "handler3": 0}
    
    def handler1(event: DomainEvent):
        call_counts["handler1"] += 1
    
    def handler2(event: DomainEvent):
        call_counts["handler2"] += 1
    
    def handler3(event: DomainEvent):
        call_counts["handler3"] += 1
    
    # Subscribe multiple handlers
    publisher.subscribe(JobCompletedEvent, handler1)
    publisher.subscribe(JobCompletedEvent, handler2)
    publisher.subscribe(JobCompletedEvent, handler3)
    
    # Publish event
    event = JobCompletedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        download_url="https://example.com/file",
        expire_at=datetime.utcnow() + timedelta(minutes=10)
    )
    
    publisher.publish(event)
    
    # Verify all handlers were called
    assert call_counts["handler1"] == 1, "Handler 1 should be called once"
    assert call_counts["handler2"] == 1, "Handler 2 should be called once"
    assert call_counts["handler3"] == 1, "Handler 3 should be called once"
    
    print("✓ All handlers called successfully")
    return True


def test_publish_dispatches_to_correct_handlers():
    """
    Test that publish dispatches events only to handlers for that event type.
    
    Verifies that handlers registered for different event types are not
    called when an unrelated event is published.
    """
    print("\n=== Testing Publish Dispatches to Correct Handlers ===")
    
    publisher = EventPublisher()
    call_counts = {"started": 0, "completed": 0, "failed": 0}
    
    def started_handler(event: DomainEvent):
        call_counts["started"] += 1
    
    def completed_handler(event: DomainEvent):
        call_counts["completed"] += 1
    
    def failed_handler(event: DomainEvent):
        call_counts["failed"] += 1
    
    # Subscribe handlers for different event types
    publisher.subscribe(JobStartedEvent, started_handler)
    publisher.subscribe(JobCompletedEvent, completed_handler)
    publisher.subscribe(JobFailedEvent, failed_handler)
    
    # Publish JobStartedEvent
    started_event = JobStartedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        url="https://youtube.com/watch?v=test",
        format_id="137+140"
    )
    publisher.publish(started_event)
    
    assert call_counts["started"] == 1, "Started handler should be called"
    assert call_counts["completed"] == 0, "Completed handler should not be called"
    assert call_counts["failed"] == 0, "Failed handler should not be called"
    
    # Publish JobCompletedEvent
    completed_event = JobCompletedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        download_url="https://example.com/file",
        expire_at=datetime.utcnow() + timedelta(minutes=10)
    )
    publisher.publish(completed_event)
    
    assert call_counts["started"] == 1, "Started handler should still be 1"
    assert call_counts["completed"] == 1, "Completed handler should be called"
    assert call_counts["failed"] == 0, "Failed handler should not be called"
    
    print("✓ Events dispatched to correct handlers only")
    return True


def test_handler_exceptions_dont_break_publishing():
    """
    Test that exceptions in handlers don't prevent other handlers from executing.
    
    Verifies that the EventPublisher catches handler exceptions and continues
    dispatching to remaining handlers.
    """
    print("\n=== Testing Handler Exceptions Don't Break Publishing ===")
    
    publisher = EventPublisher()
    call_counts = {"handler1": 0, "handler2": 0, "handler3": 0}
    
    def handler1(event: DomainEvent):
        call_counts["handler1"] += 1
    
    def handler2_raises(event: DomainEvent):
        call_counts["handler2"] += 1
        raise ValueError("Handler 2 intentionally raises exception")
    
    def handler3(event: DomainEvent):
        call_counts["handler3"] += 1
    
    # Subscribe handlers (handler2 will raise exception)
    publisher.subscribe(JobFailedEvent, handler1)
    publisher.subscribe(JobFailedEvent, handler2_raises)
    publisher.subscribe(JobFailedEvent, handler3)
    
    # Publish event
    event = JobFailedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        error_message="Test error",
        error_category="TEST_ERROR"
    )
    
    # Should not raise exception
    publisher.publish(event)
    
    # Verify all handlers were called despite exception in handler2
    assert call_counts["handler1"] == 1, "Handler 1 should be called"
    assert call_counts["handler2"] == 1, "Handler 2 should be called (before exception)"
    assert call_counts["handler3"] == 1, "Handler 3 should be called (after exception)"
    
    print("✓ All handlers executed despite exception in one handler")
    return True


def test_publish_with_no_handlers():
    """
    Test that publishing an event with no registered handlers doesn't fail.
    
    Verifies that the EventPublisher handles the case where no handlers
    are registered for an event type.
    """
    print("\n=== Testing Publish with No Handlers ===")
    
    publisher = EventPublisher()
    
    # Publish event with no handlers registered
    event = JobProgressUpdatedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        progress=JobProgress(percentage=50, phase="Downloading")
    )
    
    # Should not raise exception
    publisher.publish(event)
    
    print("✓ Publishing with no handlers succeeded")
    return True


def test_thread_safety_concurrent_publishes():
    """
    Test thread safety with concurrent event publishing.
    
    Verifies that the EventPublisher can handle concurrent publishes
    from multiple threads without race conditions.
    """
    print("\n=== Testing Thread Safety with Concurrent Publishes ===")
    
    publisher = EventPublisher()
    call_counts = {"handler": 0}
    lock = threading.Lock()
    
    def handler(event: DomainEvent):
        with lock:
            call_counts["handler"] += 1
    
    # Subscribe handler
    publisher.subscribe(JobStartedEvent, handler)
    
    # Create multiple threads that publish events concurrently
    num_threads = 10
    events_per_thread = 5
    threads: List[threading.Thread] = []
    
    def publish_events():
        for i in range(events_per_thread):
            event = JobStartedEvent(
                aggregate_id=f"job-{threading.current_thread().name}-{i}",
                occurred_at=datetime.utcnow(),
                url="https://youtube.com/watch?v=test",
                format_id="137+140"
            )
            publisher.publish(event)
    
    # Start threads
    for i in range(num_threads):
        thread = threading.Thread(target=publish_events, name=f"thread-{i}")
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all events were handled
    expected_calls = num_threads * events_per_thread
    assert call_counts["handler"] == expected_calls, \
        f"Expected {expected_calls} handler calls, got {call_counts['handler']}"
    
    print(f"✓ Thread safety verified: {expected_calls} concurrent publishes handled correctly")
    return True


def test_thread_safety_concurrent_subscribes():
    """
    Test thread safety with concurrent handler subscriptions.
    
    Verifies that the EventPublisher can handle concurrent subscribe
    operations from multiple threads without race conditions.
    """
    print("\n=== Testing Thread Safety with Concurrent Subscribes ===")
    
    publisher = EventPublisher()
    call_counts = {}
    lock = threading.Lock()
    
    def create_handler(handler_id: int):
        def handler(event: DomainEvent):
            with lock:
                if handler_id not in call_counts:
                    call_counts[handler_id] = 0
                call_counts[handler_id] += 1
        return handler
    
    # Create multiple threads that subscribe handlers concurrently
    num_threads = 10
    threads: List[threading.Thread] = []
    
    def subscribe_handler(handler_id: int):
        handler = create_handler(handler_id)
        publisher.subscribe(JobCompletedEvent, handler)
    
    # Start threads
    for i in range(num_threads):
        thread = threading.Thread(target=subscribe_handler, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Publish event to verify all handlers were registered
    event = JobCompletedEvent(
        aggregate_id="job-123",
        occurred_at=datetime.utcnow(),
        download_url="https://example.com/file",
        expire_at=datetime.utcnow() + timedelta(minutes=10)
    )
    publisher.publish(event)
    
    # Verify all handlers were called
    assert len(call_counts) == num_threads, \
        f"Expected {num_threads} handlers, got {len(call_counts)}"
    
    for handler_id, count in call_counts.items():
        assert count == 1, f"Handler {handler_id} should be called once, got {count}"
    
    print(f"✓ Thread safety verified: {num_threads} concurrent subscribes handled correctly")
    return True


def test_event_data_passed_correctly():
    """
    Test that event data is passed correctly to handlers.
    
    Verifies that handlers receive the complete event object with all
    attributes intact.
    """
    print("\n=== Testing Event Data Passed Correctly ===")
    
    publisher = EventPublisher()
    received_events = []
    
    def handler(event: DomainEvent):
        received_events.append(event)
    
    publisher.subscribe(JobCompletedEvent, handler)
    
    # Create event with specific data
    expected_url = "https://example.com/download/file.mp4"
    expected_job_id = "job-abc-123"
    expected_expire_at = datetime.utcnow() + timedelta(minutes=10)
    
    event = JobCompletedEvent(
        aggregate_id=expected_job_id,
        occurred_at=datetime.utcnow(),
        download_url=expected_url,
        expire_at=expected_expire_at
    )
    
    publisher.publish(event)
    
    # Verify event data
    assert len(received_events) == 1, "Should receive one event"
    received_event = received_events[0]
    
    assert received_event.aggregate_id == expected_job_id, "Job ID should match"
    assert received_event.download_url == expected_url, "Download URL should match"
    assert received_event.expire_at == expected_expire_at, "Expire time should match"
    
    print("✓ Event data passed correctly to handler")
    return True


def run_all_tests():
    """Run all EventPublisher tests."""
    print("\n" + "=" * 60)
    print("EVENT PUBLISHER UNIT TESTS")
    print("=" * 60)
    
    tests = [
        ("Subscribe Registers Handlers", test_subscribe_registers_handlers),
        ("Multiple Handlers for Same Event", test_subscribe_multiple_handlers),
        ("Publish Dispatches to Correct Handlers", test_publish_dispatches_to_correct_handlers),
        ("Handler Exceptions Don't Break Publishing", test_handler_exceptions_dont_break_publishing),
        ("Publish with No Handlers", test_publish_with_no_handlers),
        ("Thread Safety - Concurrent Publishes", test_thread_safety_concurrent_publishes),
        ("Thread Safety - Concurrent Subscribes", test_thread_safety_concurrent_subscribes),
        ("Event Data Passed Correctly", test_event_data_passed_correctly),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            failed += 1
            print(f"✗ {test_name} FAILED with exception: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
