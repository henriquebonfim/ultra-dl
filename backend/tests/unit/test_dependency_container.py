"""
Unit Tests for Dependency Container

Tests the DependencyContainer for service registration and resolution.
Requirements: 9.4
"""

import threading
import time
from typing import List

from application.dependency_container import DependencyContainer, DependencyNotFoundError


# Test classes for dependency injection
class ServiceInterface:
    """Base interface for testing."""
    def get_name(self) -> str:
        raise NotImplementedError


class ConcreteService(ServiceInterface):
    """Concrete implementation for testing."""
    def __init__(self, name: str = "ConcreteService"):
        self.name = name
        self.call_count = 0
    
    def get_name(self) -> str:
        self.call_count += 1
        return self.name


class AnotherService:
    """Another service for testing multiple registrations."""
    def __init__(self, value: int = 42):
        self.value = value


class DependentService:
    """Service that depends on other services."""
    def __init__(self, service: ServiceInterface, another: AnotherService):
        self.service = service
        self.another = another



def test_singleton_registration_and_resolution():
    """
    Test that singleton registration returns the same instance on each resolution.
    
    Verifies that the container maintains a single instance for singleton registrations.
    """
    print("\n=== Testing Singleton Registration and Resolution ===")
    
    container = DependencyContainer()
    service = ConcreteService("SingletonService")
    
    # Register as singleton
    container.register_singleton(ServiceInterface, service)
    
    # Resolve multiple times
    resolved1 = container.resolve(ServiceInterface)
    resolved2 = container.resolve(ServiceInterface)
    resolved3 = container.resolve(ServiceInterface)
    
    # Verify same instance
    assert resolved1 is service, "Should return the registered instance"
    assert resolved2 is service, "Should return the same instance"
    assert resolved3 is service, "Should return the same instance"
    assert resolved1 is resolved2, "All resolutions should be the same instance"
    
    print("✓ Singleton registration and resolution working correctly")
    return True


def test_transient_registration_and_resolution():
    """
    Test that transient registration creates new instances on each resolution.
    
    Verifies that the container creates a new instance for each transient resolution.
    """
    print("\n=== Testing Transient Registration and Resolution ===")
    
    container = DependencyContainer()
    counter = [0]
    
    # Factory that creates new instances
    def factory():
        counter[0] += 1
        return ConcreteService(f"TransientService-{counter[0]}")
    
    # Register as transient
    container.register_transient(ServiceInterface, factory)
    
    # Resolve multiple times
    resolved1 = container.resolve(ServiceInterface)
    resolved2 = container.resolve(ServiceInterface)
    resolved3 = container.resolve(ServiceInterface)
    
    # Verify different instances
    assert resolved1 is not resolved2, "Should create new instance"
    assert resolved2 is not resolved3, "Should create new instance"
    assert resolved1 is not resolved3, "Should create new instance"
    
    # Verify factory was called for each resolution
    assert counter[0] == 3, f"Factory should be called 3 times, got {counter[0]}"
    
    # Verify each instance has unique name
    assert resolved1.get_name() == "TransientService-1"
    assert resolved2.get_name() == "TransientService-2"
    assert resolved3.get_name() == "TransientService-3"
    
    print("✓ Transient registration and resolution working correctly")
    return True


def test_override_for_testing():
    """
    Test that override allows replacing services for testing.
    
    Verifies that overrides take precedence over both singleton and transient registrations.
    """
    print("\n=== Testing Override for Testing ===")
    
    container = DependencyContainer()
    
    # Register original service as singleton
    original_service = ConcreteService("OriginalService")
    container.register_singleton(ServiceInterface, original_service)
    
    # Verify original service is resolved
    resolved = container.resolve(ServiceInterface)
    assert resolved is original_service, "Should resolve original service"
    
    # Override with mock service
    mock_service = ConcreteService("MockService")
    container.override(ServiceInterface, mock_service)
    
    # Verify mock service is resolved
    resolved_after_override = container.resolve(ServiceInterface)
    assert resolved_after_override is mock_service, "Should resolve mock service"
    assert resolved_after_override is not original_service, "Should not resolve original service"
    
    # Clear overrides
    container.clear_overrides()
    
    # Verify original service is resolved again
    resolved_after_clear = container.resolve(ServiceInterface)
    assert resolved_after_clear is original_service, "Should resolve original service after clearing overrides"
    
    print("✓ Override for testing working correctly")
    return True



def test_override_transient_service():
    """
    Test that override works with transient services.
    
    Verifies that overrides take precedence over transient registrations.
    """
    print("\n=== Testing Override Transient Service ===")
    
    container = DependencyContainer()
    counter = [0]
    
    # Register transient service
    def factory():
        counter[0] += 1
        return ConcreteService(f"TransientService-{counter[0]}")
    
    container.register_transient(ServiceInterface, factory)
    
    # Resolve transient service
    resolved1 = container.resolve(ServiceInterface)
    assert counter[0] == 1, "Factory should be called once"
    
    # Override with mock
    mock_service = ConcreteService("MockService")
    container.override(ServiceInterface, mock_service)
    
    # Resolve should return mock, not call factory
    resolved2 = container.resolve(ServiceInterface)
    assert resolved2 is mock_service, "Should resolve mock service"
    assert counter[0] == 1, "Factory should not be called after override"
    
    print("✓ Override transient service working correctly")
    return True


def test_resolve_raises_error_for_unregistered_types():
    """
    Test that resolve raises DependencyNotFoundError for unregistered types.
    
    Verifies that attempting to resolve an unregistered service raises an appropriate error.
    """
    print("\n=== Testing Resolve Raises Error for Unregistered Types ===")
    
    container = DependencyContainer()
    
    # Attempt to resolve unregistered service
    try:
        container.resolve(ServiceInterface)
        assert False, "Should raise DependencyNotFoundError"
    except DependencyNotFoundError as e:
        assert "ServiceInterface" in str(e), "Error message should include type name"
        print(f"✓ Correctly raised DependencyNotFoundError: {e}")
    
    # Register a different service
    container.register_singleton(AnotherService, AnotherService())
    
    # Attempt to resolve still unregistered service
    try:
        container.resolve(ServiceInterface)
        assert False, "Should still raise DependencyNotFoundError"
    except DependencyNotFoundError as e:
        assert "ServiceInterface" in str(e), "Error message should include type name"
        print(f"✓ Correctly raised DependencyNotFoundError for different type: {e}")
    
    return True


def test_multiple_service_types():
    """
    Test registering and resolving multiple different service types.
    
    Verifies that the container can manage multiple service types independently.
    """
    print("\n=== Testing Multiple Service Types ===")
    
    container = DependencyContainer()
    
    # Register multiple services
    service1 = ConcreteService("Service1")
    service2 = AnotherService(100)
    
    container.register_singleton(ServiceInterface, service1)
    container.register_singleton(AnotherService, service2)
    
    # Resolve each service
    resolved1 = container.resolve(ServiceInterface)
    resolved2 = container.resolve(AnotherService)
    
    # Verify correct services resolved
    assert resolved1 is service1, "Should resolve ServiceInterface"
    assert resolved2 is service2, "Should resolve AnotherService"
    assert resolved1.get_name() == "Service1"
    assert resolved2.value == 100
    
    print("✓ Multiple service types working correctly")
    return True



def test_is_registered():
    """
    Test is_registered method for checking service registration.
    
    Verifies that is_registered correctly identifies registered and unregistered services.
    """
    print("\n=== Testing is_registered Method ===")
    
    container = DependencyContainer()
    
    # Check unregistered service
    assert not container.is_registered(ServiceInterface), "Should not be registered"
    
    # Register singleton
    container.register_singleton(ServiceInterface, ConcreteService())
    assert container.is_registered(ServiceInterface), "Should be registered"
    
    # Register transient
    container.register_transient(AnotherService, lambda: AnotherService())
    assert container.is_registered(AnotherService), "Should be registered"
    
    # Check unregistered service
    assert not container.is_registered(DependentService), "Should not be registered"
    
    # Override
    container.override(DependentService, DependentService(ConcreteService(), AnotherService()))
    assert container.is_registered(DependentService), "Should be registered after override"
    
    print("✓ is_registered method working correctly")
    return True


def test_get_registration_type():
    """
    Test get_registration_type method for identifying registration types.
    
    Verifies that get_registration_type correctly identifies singleton, transient, and override registrations.
    """
    print("\n=== Testing get_registration_type Method ===")
    
    container = DependencyContainer()
    
    # Check unregistered service
    assert container.get_registration_type(ServiceInterface) == 'not_registered'
    
    # Register singleton
    container.register_singleton(ServiceInterface, ConcreteService())
    assert container.get_registration_type(ServiceInterface) == 'singleton'
    
    # Register transient
    container.register_transient(AnotherService, lambda: AnotherService())
    assert container.get_registration_type(AnotherService) == 'transient'
    
    # Override singleton
    container.override(ServiceInterface, ConcreteService("Override"))
    assert container.get_registration_type(ServiceInterface) == 'override'
    
    # Clear overrides
    container.clear_overrides()
    assert container.get_registration_type(ServiceInterface) == 'singleton'
    
    print("✓ get_registration_type method working correctly")
    return True


def test_thread_safety_concurrent_resolutions():
    """
    Test thread safety with concurrent service resolutions.
    
    Verifies that the container can handle concurrent resolve operations
    from multiple threads without race conditions.
    """
    print("\n=== Testing Thread Safety with Concurrent Resolutions ===")
    
    container = DependencyContainer()
    service = ConcreteService("ThreadSafeService")
    container.register_singleton(ServiceInterface, service)
    
    resolved_services: List[ServiceInterface] = []
    lock = threading.Lock()
    
    def resolve_service():
        resolved = container.resolve(ServiceInterface)
        with lock:
            resolved_services.append(resolved)
    
    # Create multiple threads that resolve concurrently
    num_threads = 20
    threads: List[threading.Thread] = []
    
    for i in range(num_threads):
        thread = threading.Thread(target=resolve_service)
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all threads got the same instance
    assert len(resolved_services) == num_threads, f"Expected {num_threads} resolutions"
    for resolved in resolved_services:
        assert resolved is service, "All threads should get the same singleton instance"
    
    print(f"✓ Thread safety verified: {num_threads} concurrent resolutions handled correctly")
    return True



def test_thread_safety_concurrent_registrations():
    """
    Test thread safety with concurrent service registrations.
    
    Verifies that the container can handle concurrent register operations
    from multiple threads without race conditions.
    """
    print("\n=== Testing Thread Safety with Concurrent Registrations ===")
    
    container = DependencyContainer()
    
    # Create unique service types for each thread
    class Service1: pass
    class Service2: pass
    class Service3: pass
    class Service4: pass
    class Service5: pass
    
    service_types = [Service1, Service2, Service3, Service4, Service5]
    
    def register_service(service_type):
        instance = service_type()
        container.register_singleton(service_type, instance)
    
    # Create multiple threads that register concurrently
    threads: List[threading.Thread] = []
    
    for service_type in service_types:
        thread = threading.Thread(target=register_service, args=(service_type,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all services are registered
    for service_type in service_types:
        assert container.is_registered(service_type), f"{service_type.__name__} should be registered"
        resolved = container.resolve(service_type)
        assert isinstance(resolved, service_type), f"Should resolve correct type"
    
    print(f"✓ Thread safety verified: {len(service_types)} concurrent registrations handled correctly")
    return True


def test_thread_safety_concurrent_overrides():
    """
    Test thread safety with concurrent override operations.
    
    Verifies that the container can handle concurrent override operations
    from multiple threads without race conditions.
    """
    print("\n=== Testing Thread Safety with Concurrent Overrides ===")
    
    container = DependencyContainer()
    
    # Register original service
    original_service = ConcreteService("Original")
    container.register_singleton(ServiceInterface, original_service)
    
    override_count = [0]
    lock = threading.Lock()
    
    def override_service(thread_id: int):
        mock_service = ConcreteService(f"Mock-{thread_id}")
        container.override(ServiceInterface, mock_service)
        with lock:
            override_count[0] += 1
        time.sleep(0.001)  # Small delay to increase chance of race conditions
    
    # Create multiple threads that override concurrently
    num_threads = 10
    threads: List[threading.Thread] = []
    
    for i in range(num_threads):
        thread = threading.Thread(target=override_service, args=(i,))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Verify all overrides were processed
    assert override_count[0] == num_threads, f"Expected {num_threads} overrides"
    
    # Verify service is still resolvable (last override wins)
    resolved = container.resolve(ServiceInterface)
    assert resolved is not original_service, "Should resolve override, not original"
    
    print(f"✓ Thread safety verified: {num_threads} concurrent overrides handled correctly")
    return True


def test_transient_with_dependencies():
    """
    Test transient registration with factory that creates services with dependencies.
    
    Verifies that transient factories can create complex services with dependencies.
    """
    print("\n=== Testing Transient with Dependencies ===")
    
    container = DependencyContainer()
    
    # Register dependencies as singletons
    service = ConcreteService("DependencyService")
    another = AnotherService(999)
    container.register_singleton(ServiceInterface, service)
    container.register_singleton(AnotherService, another)
    
    # Register dependent service as transient
    def factory():
        s = container.resolve(ServiceInterface)
        a = container.resolve(AnotherService)
        return DependentService(s, a)
    
    container.register_transient(DependentService, factory)
    
    # Resolve dependent service multiple times
    resolved1 = container.resolve(DependentService)
    resolved2 = container.resolve(DependentService)
    
    # Verify different instances of dependent service
    assert resolved1 is not resolved2, "Should create new instances"
    
    # Verify both have same dependencies (singletons)
    assert resolved1.service is service, "Should have same service dependency"
    assert resolved2.service is service, "Should have same service dependency"
    assert resolved1.another is another, "Should have same another dependency"
    assert resolved2.another is another, "Should have same another dependency"
    
    print("✓ Transient with dependencies working correctly")
    return True



def test_metadata_extractor_injection():
    """
    Test that metadata extractor is created as singleton and can be retrieved.
    
    Verifies that get_metadata_extractor returns the same instance on multiple calls.
    Requirements: 5.1, 5.3
    """
    print("\n=== Testing Metadata Extractor Injection ===")
    
    container = DependencyContainer()
    
    # Get metadata extractor multiple times
    extractor1 = container.get_metadata_extractor()
    extractor2 = container.get_metadata_extractor()
    extractor3 = container.get_metadata_extractor()
    
    # Verify same instance (singleton)
    assert extractor1 is extractor2, "Should return same instance"
    assert extractor2 is extractor3, "Should return same instance"
    
    # Verify it's the correct type
    from infrastructure.video_metadata_extractor import VideoMetadataExtractor
    assert isinstance(extractor1, VideoMetadataExtractor), "Should be VideoMetadataExtractor instance"
    
    print("✓ Metadata extractor injection working correctly")
    return True


def test_storage_repository_injection():
    """
    Test that storage repository is created as singleton via StorageFactory.
    
    Verifies that get_storage_repository returns the same instance on multiple calls.
    Requirements: 8.4
    """
    print("\n=== Testing Storage Repository Injection ===")
    
    container = DependencyContainer()
    
    # Get storage repository multiple times
    storage1 = container.get_storage_repository()
    storage2 = container.get_storage_repository()
    storage3 = container.get_storage_repository()
    
    # Verify same instance (singleton)
    assert storage1 is storage2, "Should return same instance"
    assert storage2 is storage3, "Should return same instance"
    
    # Verify it implements the interface
    from domain.file_storage.storage_repository import IFileStorageRepository
    assert isinstance(storage1, IFileStorageRepository), "Should implement IFileStorageRepository"
    
    print("✓ Storage repository injection working correctly")
    return True


def test_video_processor_creation_with_dependency():
    """
    Test that VideoProcessor is created with injected metadata extractor.
    
    Verifies that create_video_processor injects the metadata extractor dependency.
    Requirements: 5.1, 5.3
    """
    print("\n=== Testing VideoProcessor Creation with Dependency ===")
    
    container = DependencyContainer()
    
    # Create video processor
    processor1 = container.create_video_processor()
    processor2 = container.create_video_processor()
    
    # Verify processors are different instances (not singleton)
    assert processor1 is not processor2, "Should create new instances"
    
    # Verify both have the same metadata extractor (singleton)
    assert processor1.metadata_extractor is processor2.metadata_extractor, \
        "Should share same metadata extractor singleton"
    
    # Verify metadata extractor is injected
    from infrastructure.video_metadata_extractor import VideoMetadataExtractor
    assert isinstance(processor1.metadata_extractor, VideoMetadataExtractor), \
        "Should have VideoMetadataExtractor injected"
    
    # Verify it's the same as get_metadata_extractor
    extractor = container.get_metadata_extractor()
    assert processor1.metadata_extractor is extractor, \
        "Should use same metadata extractor from container"
    
    print("✓ VideoProcessor creation with dependency injection working correctly")
    return True


def test_event_handler_setup():
    """
    Test that event handlers are properly registered with event publisher.
    
    Verifies that setup_event_handlers registers LoggingEventHandler by default.
    Requirements: 4.3, 4.4, 5.5
    """
    print("\n=== Testing Event Handler Setup ===")
    
    container = DependencyContainer()
    
    # Create mock event publisher
    from application.event_publisher import EventPublisher
    event_publisher = EventPublisher()
    
    # Setup event handlers
    container.setup_event_handlers(event_publisher)
    
    # Verify handlers were registered
    from domain.events import DomainEvent
    assert DomainEvent in event_publisher._handlers, "Should register DomainEvent handlers"
    assert len(event_publisher._handlers[DomainEvent]) > 0, "Should have at least one handler"
    
    print("✓ Event handler setup working correctly")
    return True


def test_event_handler_setup_with_custom_handlers():
    """
    Test that custom event handlers can be registered.
    
    Verifies that setup_event_handlers accepts custom handler classes.
    Requirements: 4.3, 4.4, 5.5
    """
    print("\n=== Testing Event Handler Setup with Custom Handlers ===")
    
    container = DependencyContainer()
    
    # Create mock event publisher
    from application.event_publisher import EventPublisher
    event_publisher = EventPublisher()
    
    # Create custom handler class
    class CustomEventHandler:
        def __init__(self):
            self.handled_events = []
        
        def handle(self, event):
            self.handled_events.append(event)
    
    # Setup with custom handler
    from infrastructure.event_handlers.logging_handler import LoggingEventHandler
    container.setup_event_handlers(event_publisher, [LoggingEventHandler, CustomEventHandler])
    
    # Verify handlers were registered
    from domain.events import DomainEvent
    assert DomainEvent in event_publisher._handlers, "Should register DomainEvent handlers"
    # Should have 2 handlers (LoggingEventHandler + CustomEventHandler)
    assert len(event_publisher._handlers[DomainEvent]) == 2, "Should have 2 handlers"
    
    print("✓ Event handler setup with custom handlers working correctly")
    return True


def run_all_tests():
    """Run all DependencyContainer tests."""
    print("\n" + "=" * 60)
    print("DEPENDENCY CONTAINER UNIT TESTS")
    print("=" * 60)
    
    tests = [
        ("Singleton Registration and Resolution", test_singleton_registration_and_resolution),
        ("Transient Registration and Resolution", test_transient_registration_and_resolution),
        ("Override for Testing", test_override_for_testing),
        ("Override Transient Service", test_override_transient_service),
        ("Resolve Raises Error for Unregistered Types", test_resolve_raises_error_for_unregistered_types),
        ("Multiple Service Types", test_multiple_service_types),
        ("is_registered Method", test_is_registered),
        ("get_registration_type Method", test_get_registration_type),
        ("Thread Safety - Concurrent Resolutions", test_thread_safety_concurrent_resolutions),
        ("Thread Safety - Concurrent Registrations", test_thread_safety_concurrent_registrations),
        ("Thread Safety - Concurrent Overrides", test_thread_safety_concurrent_overrides),
        ("Transient with Dependencies", test_transient_with_dependencies),
        ("Metadata Extractor Injection", test_metadata_extractor_injection),
        ("Storage Repository Injection", test_storage_repository_injection),
        ("VideoProcessor Creation with Dependency", test_video_processor_creation_with_dependency),
        ("Event Handler Setup", test_event_handler_setup),
        ("Event Handler Setup with Custom Handlers", test_event_handler_setup_with_custom_handlers),
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
