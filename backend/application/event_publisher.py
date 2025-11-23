"""
Event Publisher

Application service for publishing domain events to registered handlers.
Enables decoupling of side effects from core business logic.
"""

import logging
from threading import Lock
from typing import Callable, Dict, List, Type

from domain.events import DomainEvent

logger = logging.getLogger(__name__)


class EventPublisher:
    """
    Event publisher that dispatches domain events to registered handlers.
    
    The EventPublisher maintains a registry of event types to handler functions
    and dispatches events synchronously to all registered handlers. Handler
    exceptions are caught and logged to prevent side effects from breaking
    core business logic.
    
    Thread-safe for concurrent event publishing.
    """
    
    def __init__(self):
        """Initialize EventPublisher with empty handler registry."""
        self._handlers: Dict[Type[DomainEvent], List[Callable[[DomainEvent], None]]] = {}
        self._lock = Lock()
    
    def subscribe(
        self,
        event_type: Type[DomainEvent],
        handler: Callable[[DomainEvent], None]
    ) -> None:
        """
        Register a handler for a specific event type.
        
        Args:
            event_type: The type of domain event to handle
            handler: Callable that accepts the event as parameter
            
        Example:
            publisher = EventPublisher()
            publisher.subscribe(JobCompletedEvent, handle_job_completed)
        """
        with self._lock:
            if event_type not in self._handlers:
                self._handlers[event_type] = []
            
            self._handlers[event_type].append(handler)
            logger.debug(
                f"Registered handler {handler.__name__} for {event_type.__name__}"
            )
    
    def publish(self, event: DomainEvent) -> None:
        """
        Publish an event to all registered handlers.
        
        Dispatches the event synchronously to all handlers registered for
        the event's type. Handler exceptions are caught and logged to prevent
        side effects from breaking core business logic.
        
        Args:
            event: The domain event to publish
            
        Example:
            event = JobCompletedEvent(
                aggregate_id="job-123",
                occurred_at=datetime.utcnow(),
                download_url="https://example.com/file",
                expire_at=datetime.utcnow() + timedelta(minutes=10)
            )
            publisher.publish(event)
        """
        event_type = type(event)
        
        with self._lock:
            handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            logger.debug(f"No handlers registered for {event_type.__name__}")
            return
        
        logger.debug(
            f"Publishing {event_type.__name__} to {len(handlers)} handler(s)"
        )
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # Log but don't fail - side effects should not break core logic
                logger.error(
                    f"Error in handler {handler.__name__} for {event_type.__name__}: {e}",
                    exc_info=True
                )
