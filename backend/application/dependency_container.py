"""
Dependency Injection Container

Manages service lifecycles and dependency resolution.
Requirements: 7.1, 7.5, 5.1, 5.3, 5.5
"""

import logging
import threading
from typing import Any, Callable, Dict, List, Type, TypeVar, Optional

logger = logging.getLogger(__name__)

T = TypeVar('T')


class DependencyNotFoundError(Exception):
    """Raised when attempting to resolve an unregistered dependency."""
    pass


class DependencyContainer:
    """
    Dependency injection container for managing service lifecycles.
    
    Supports singleton (single instance) and transient (factory-created)
    registration patterns. Thread-safe for concurrent access.
    """
    
    def __init__(self):
        """Initialize the dependency container."""
        self._singletons: Dict[Type, Any] = {}
        self._transients: Dict[Type, Callable[[], Any]] = {}
        self._overrides: Dict[Type, Any] = {}
        self._lock = threading.Lock()
        
        # Infrastructure components (lazy-initialized)
        self._metadata_extractor: Optional[Any] = None
        self._storage_repository: Optional[Any] = None
        
        logger.debug("DependencyContainer initialized")
    
    def register_singleton(self, interface: Type[T], implementation: T) -> None:
        """
        Register a singleton service (single instance shared across all resolutions).
        
        Args:
            interface: The interface or class type to register
            implementation: The concrete instance to use
            
        Example:
            container.register_singleton(JobManager, job_manager_instance)
        """
        with self._lock:
            self._singletons[interface] = implementation
            logger.debug(f"Registered singleton: {interface.__name__}")
    
    def register_transient(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a transient service (new instance created on each resolution).
        
        Args:
            interface: The interface or class type to register
            factory: A callable that creates new instances
            
        Example:
            container.register_transient(
                DownloadService,
                lambda: DownloadService(job_manager, file_manager)
            )
        """
        with self._lock:
            self._transients[interface] = factory
            logger.debug(f"Registered transient: {interface.__name__}")
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a registered service.
        
        Args:
            interface: The interface or class type to resolve
            
        Returns:
            The resolved service instance
            
        Raises:
            DependencyNotFoundError: If the interface is not registered
            
        Example:
            download_service = container.resolve(DownloadService)
        """
        # Determine what to resolve while holding the lock
        with self._lock:
            # Check for overrides first (for testing)
            if interface in self._overrides:
                logger.debug(f"Resolved override: {interface.__name__}")
                return self._overrides[interface]
            
            # Check for singleton
            if interface in self._singletons:
                logger.debug(f"Resolved singleton: {interface.__name__}")
                return self._singletons[interface]
            
            # Check for transient - get factory but don't call it yet
            if interface in self._transients:
                logger.debug(f"Resolved transient: {interface.__name__}")
                factory = self._transients[interface]
                # Release lock before calling factory to avoid deadlock
                # if factory needs to resolve other dependencies
            else:
                # Not found
                raise DependencyNotFoundError(
                    f"No registration found for type: {interface.__name__}"
                )
        
        # Call factory outside the lock to allow nested resolve calls
        return factory()
    
    def override(self, interface: Type[T], implementation: T) -> None:
        """
        Override a registered service (primarily for testing).
        
        Overrides take precedence over both singleton and transient registrations.
        
        Args:
            interface: The interface or class type to override
            implementation: The mock or test instance to use
            
        Example:
            container.override(JobManager, mock_job_manager)
        """
        with self._lock:
            self._overrides[interface] = implementation
            logger.debug(f"Overridden: {interface.__name__}")
    
    def clear_overrides(self) -> None:
        """
        Clear all overrides.
        
        Useful for cleaning up after tests.
        """
        with self._lock:
            self._overrides.clear()
            logger.debug("Cleared all overrides")
    
    def is_registered(self, interface: Type) -> bool:
        """
        Check if an interface is registered.
        
        Args:
            interface: The interface or class type to check
            
        Returns:
            True if registered (singleton, transient, or override)
        """
        with self._lock:
            return (
                interface in self._singletons or
                interface in self._transients or
                interface in self._overrides
            )
    
    def get_registration_type(self, interface: Type) -> str:
        """
        Get the registration type for an interface.
        
        Args:
            interface: The interface or class type to check
            
        Returns:
            'singleton', 'transient', 'override', or 'not_registered'
        """
        with self._lock:
            if interface in self._overrides:
                return 'override'
            if interface in self._singletons:
                return 'singleton'
            if interface in self._transients:
                return 'transient'
            return 'not_registered'
    
    def get_metadata_extractor(self):
        """
        Get or create VideoMetadataExtractor singleton.
        
        Returns:
            IVideoMetadataExtractor implementation
            
        Requirements: 5.1, 5.3
        """
        if self._metadata_extractor is None:
            from infrastructure.video_metadata_extractor import VideoMetadataExtractor
            self._metadata_extractor = VideoMetadataExtractor()
            logger.debug("Created VideoMetadataExtractor singleton")
        
        return self._metadata_extractor
    
    def get_storage_repository(self):
        """
        Get or create storage repository singleton using StorageFactory.
        
        Returns:
            IFileStorageRepository implementation (Local or GCS based on environment)
            
        Requirements: 8.4
        """
        if self._storage_repository is None:
            from infrastructure.storage_factory import StorageFactory
            self._storage_repository = StorageFactory.create_storage()
            logger.debug("Created storage repository singleton via StorageFactory")
        
        return self._storage_repository
    
    def create_video_processor(self):
        """
        Create VideoProcessor with injected metadata extractor dependency.
        
        Returns:
            VideoProcessor instance with IVideoMetadataExtractor injected
            
        Requirements: 5.1, 5.3
        """
        from domain.video_processing.services import VideoProcessor
        
        metadata_extractor = self.get_metadata_extractor()
        video_processor = VideoProcessor(metadata_extractor)
        
        logger.debug("Created VideoProcessor with injected metadata extractor")
        return video_processor
    
    def setup_event_handlers(self, event_publisher, event_handler_classes: List[Type] = None) -> None:
        """
        Setup infrastructure event handlers and subscribe them to the event publisher.
        
        This method registers infrastructure event handlers (like LoggingEventHandler)
        with the event publisher, maintaining the separation between domain and infrastructure.
        
        Args:
            event_publisher: EventPublisher instance to subscribe handlers to
            event_handler_classes: Optional list of event handler classes to instantiate and register.
                                  If None, registers default handlers (LoggingEventHandler).
        
        Example:
            container.setup_event_handlers(event_publisher)
            # or with custom handlers
            container.setup_event_handlers(event_publisher, [LoggingEventHandler, CustomHandler])
        
        Requirements: 4.3, 4.4, 5.5
        """
        from infrastructure.event_handlers.logging_handler import LoggingEventHandler
        
        # Use default handlers if none specified
        if event_handler_classes is None:
            event_handler_classes = [LoggingEventHandler]
        
        for handler_class in event_handler_classes:
            try:
                # Instantiate handler
                if handler_class == LoggingEventHandler:
                    # LoggingEventHandler needs a logger instance
                    handler_logger = logging.getLogger("ultradl")
                    handler = handler_class(handler_logger)
                else:
                    # Other handlers may have different constructors
                    handler = handler_class()
                
                # Subscribe handler to all domain events
                # The handler's handle() method will dispatch to specific event handlers
                from domain.events import DomainEvent
                event_publisher.subscribe(DomainEvent, handler.handle)
                
                logger.debug(f"Registered event handler: {handler_class.__name__}")
            except Exception as e:
                logger.error(f"Failed to register event handler {handler_class.__name__}: {e}")
                # Don't fail initialization if event handler setup fails
                continue
