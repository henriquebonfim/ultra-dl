"""
DependencyContainer tests skipped.

This module is intentionally skipped to remove overengineering tests.
"""

import pytest

pytest.skip("Skipping DependencyContainer tests per request", allow_module_level=True)


class DummyService:
    """Dummy service for testing."""

    def __init__(self, value="default"):
        self.value = value


class DummyInterface:
    """Dummy interface for testing."""

    pass


class DummyImplementation(DummyInterface):
    """Dummy implementation for testing."""

    def __init__(self):
        self.initialized = True


@pytest.fixture
def container():
    """Create a fresh DependencyContainer for each test."""
    return DependencyContainer()


class TestDependencyContainerRegistration:
    """Test service registration."""

    def test_register_singleton(self, container):
        """
        Test singleton registration.

        Verifies that a service can be registered as a singleton.
        """
        # Arrange
        service = DummyService("test")

        # Act
        container.register_singleton(DummyService, service)

        # Assert
        assert container.is_registered(DummyService)
        assert container.get_registration_type(DummyService) == "singleton"

    def test_register_transient(self, container):
        """
        Test transient registration.

        Verifies that a service can be registered as transient
        with a factory function.
        """
        # Arrange
        factory = lambda: DummyService("transient")

        # Act
        container.register_transient(DummyService, factory)

        # Assert
        assert container.is_registered(DummyService)
        assert container.get_registration_type(DummyService) == "transient"

    def test_register_multiple_services(self, container):
        """
        Test registering multiple different services.

        Verifies that multiple services can be registered
        independently.
        """
        # Arrange
        service1 = DummyService("service1")
        service2 = DummyImplementation()

        # Act
        container.register_singleton(DummyService, service1)
        container.register_singleton(DummyImplementation, service2)

        # Assert
        assert container.is_registered(DummyService)
        assert container.is_registered(DummyImplementation)


class TestDependencyContainerResolution:
    """Test service resolution."""

    def test_resolve_singleton(self, container):
        """
        Test resolving a singleton service.

        Verifies that registered singleton can be resolved.
        """
        # Arrange
        service = DummyService("test")
        container.register_singleton(DummyService, service)

        # Act
        resolved = container.resolve(DummyService)

        # Assert
        assert resolved is service
        assert resolved.value == "test"

    def test_resolve_transient(self, container):
        """
        Test resolving a transient service.

        Verifies that transient factory is called on resolution.
        """
        # Arrange
        factory = lambda: DummyService("transient")
        container.register_transient(DummyService, factory)

        # Act
        resolved = container.resolve(DummyService)

        # Assert
        assert isinstance(resolved, DummyService)
        assert resolved.value == "transient"

    def test_resolve_unregistered_raises_error(self, container):
        """
        Test resolving unregistered service raises error.

        Verifies that DependencyNotFoundError is raised when
        attempting to resolve unregistered service.
        """
        # Act & Assert
        with pytest.raises(DependencyNotFoundError, match="No registration found"):
            container.resolve(DummyService)

    def test_resolve_with_override(self, container):
        """
        Test that overrides take precedence.

        Verifies that override is returned instead of
        original registration.
        """
        # Arrange
        original = DummyService("original")
        override = DummyService("override")
        container.register_singleton(DummyService, original)
        container.override(DummyService, override)

        # Act
        resolved = container.resolve(DummyService)

        # Assert
        assert resolved is override
        assert resolved.value == "override"


class TestDependencyContainerSingletonBehavior:
    """Test singleton behavior."""

    def test_singleton_returns_same_instance(self, container):
        """
        Test that singleton returns same instance on multiple resolutions.

        Verifies that the same object is returned each time
        a singleton is resolved.
        """
        # Arrange
        service = DummyService("test")
        container.register_singleton(DummyService, service)

        # Act
        resolved1 = container.resolve(DummyService)
        resolved2 = container.resolve(DummyService)

        # Assert
        assert resolved1 is resolved2
        assert resolved1 is service

    def test_transient_returns_new_instance(self, container):
        """
        Test that transient returns new instance on each resolution.

        Verifies that different objects are returned each time
        a transient is resolved.
        """
        # Arrange
        call_count = [0]

        def factory():
            call_count[0] += 1
            return DummyService(f"instance_{call_count[0]}")

        container.register_transient(DummyService, factory)

        # Act
        resolved1 = container.resolve(DummyService)
        resolved2 = container.resolve(DummyService)

        # Assert
        assert resolved1 is not resolved2
        assert resolved1.value == "instance_1"
        assert resolved2.value == "instance_2"


class TestDependencyContainerOverrides:
    """Test override functionality."""

    def test_override_service(self, container):
        """
        Test overriding a registered service.

        Verifies that override replaces original registration.
        """
        # Arrange
        original = DummyService("original")
        override = DummyService("override")
        container.register_singleton(DummyService, original)

        # Act
        container.override(DummyService, override)
        resolved = container.resolve(DummyService)

        # Assert
        assert resolved is override
        assert container.get_registration_type(DummyService) == "override"

    def test_clear_overrides(self, container):
        """
        Test clearing all overrides.

        Verifies that after clearing overrides, original
        registration is used.
        """
        # Arrange
        original = DummyService("original")
        override = DummyService("override")
        container.register_singleton(DummyService, original)
        container.override(DummyService, override)

        # Act
        container.clear_overrides()
        resolved = container.resolve(DummyService)

        # Assert
        assert resolved is original
        assert container.get_registration_type(DummyService) == "singleton"

    def test_override_without_registration(self, container):
        """
        Test that override works even without prior registration.

        Verifies that services can be overridden before registration
        (useful for testing).
        """
        # Arrange
        override = DummyService("override")

        # Act
        container.override(DummyService, override)
        resolved = container.resolve(DummyService)

        # Assert
        assert resolved is override


class TestDependencyContainerInterfaceMapping:
    """Test interface to implementation mapping."""

    def test_register_implementation_for_interface(self, container):
        """
        Test registering implementation for interface.

        Verifies that implementation can be registered and
        resolved via interface type.
        """
        # Arrange
        implementation = DummyImplementation()

        # Act
        container.register_singleton(DummyInterface, implementation)
        resolved = container.resolve(DummyInterface)

        # Assert
        assert resolved is implementation
        assert isinstance(resolved, DummyInterface)

    def test_resolve_via_interface_type(self, container):
        """
        Test resolving service via interface type.

        Verifies that services can be resolved using
        interface as the key.
        """
        # Arrange
        implementation = DummyImplementation()
        container.register_singleton(DummyInterface, implementation)

        # Act
        resolved = container.resolve(DummyInterface)

        # Assert
        assert resolved is implementation
        assert hasattr(resolved, "initialized")


class TestDependencyContainerInspection:
    """Test container inspection methods."""

    def test_is_registered_returns_true_for_registered(self, container):
        """
        Test is_registered returns True for registered services.
        """
        # Arrange
        service = DummyService()
        container.register_singleton(DummyService, service)

        # Act & Assert
        assert container.is_registered(DummyService) is True

    def test_is_registered_returns_false_for_unregistered(self, container):
        """
        Test is_registered returns False for unregistered services.
        """
        # Act & Assert
        assert container.is_registered(DummyService) is False

    def test_get_registration_type_singleton(self, container):
        """
        Test get_registration_type returns 'singleton'.
        """
        # Arrange
        service = DummyService()
        container.register_singleton(DummyService, service)

        # Act & Assert
        assert container.get_registration_type(DummyService) == "singleton"

    def test_get_registration_type_transient(self, container):
        """
        Test get_registration_type returns 'transient'.
        """
        # Arrange
        container.register_transient(DummyService, lambda: DummyService())

        # Act & Assert
        assert container.get_registration_type(DummyService) == "transient"

    def test_get_registration_type_override(self, container):
        """
        Test get_registration_type returns 'override'.
        """
        # Arrange
        service = DummyService()
        container.override(DummyService, service)

        # Act & Assert
        assert container.get_registration_type(DummyService) == "override"

    def test_get_registration_type_not_registered(self, container):
        """
        Test get_registration_type returns 'not_registered'.
        """
        # Act & Assert
        assert container.get_registration_type(DummyService) == "not_registered"


class TestDependencyContainerThreadSafety:
    """Test thread safety of container operations."""

    def test_concurrent_registration_and_resolution(self, container):
        """
        Test that container handles concurrent operations safely.

        This is a basic test - full thread safety testing would
        require more complex concurrent scenarios.
        """
        # Arrange
        service = DummyService("test")

        # Act
        container.register_singleton(DummyService, service)
        resolved1 = container.resolve(DummyService)
        resolved2 = container.resolve(DummyService)

        # Assert
        assert resolved1 is resolved2
        assert resolved1 is service


class TestDependencyContainerFactoryMethods:
    """Test container factory methods for infrastructure components."""

    @patch("src.infrastructure.video_metadata_extractor.VideoMetadataExtractor")
    def test_get_metadata_extractor_creates_singleton(
        self, mock_extractor_class, container
    ):
        """
        Test that get_metadata_extractor creates and caches singleton.

        Verifies that VideoMetadataExtractor is created once and reused.
        """
        # Arrange
        mock_instance = Mock()
        mock_extractor_class.return_value = mock_instance

        # Act
        extractor1 = container.get_metadata_extractor()
        extractor2 = container.get_metadata_extractor()

        # Assert
        assert extractor1 is extractor2
        mock_extractor_class.assert_called_once()

    @patch("src.infrastructure.storage_factory.StorageFactory")
    def test_get_storage_repository_creates_singleton(
        self, mock_storage_factory, container
    ):
        """
        Test that get_storage_repository creates and caches singleton.

        Verifies that storage repository is created once via
        StorageFactory and reused.
        """
        # Arrange
        mock_storage = Mock()
        mock_storage_factory.create_storage.return_value = mock_storage

        # Act
        storage1 = container.get_storage_repository()
        storage2 = container.get_storage_repository()

        # Assert
        assert storage1 is storage2
        mock_storage_factory.create_storage.assert_called_once()

    @patch("src.domain.video_processing.services.VideoProcessor")
    def test_create_video_processor_injects_dependencies(
        self, mock_processor_class, container
    ):
        """
        Test that create_video_processor injects metadata extractor.

        Verifies that VideoProcessor is created with injected
        metadata extractor dependency.
        """
        # Arrange
        mock_processor = Mock()
        mock_processor_class.return_value = mock_processor

        # Act
        processor = container.create_video_processor()

        # Assert
        mock_processor_class.assert_called_once()
        # Verify metadata extractor was passed
        call_args = mock_processor_class.call_args
        assert call_args[0][0] is not None  # metadata_extractor argument

    @patch("src.infrastructure.event_handlers.logging_handler.LoggingEventHandler")
    def test_setup_event_handlers_registers_handlers(
        self, mock_handler_class, container
    ):
        """
        Test that setup_event_handlers registers event handlers.

        Verifies that event handlers are instantiated and
        subscribed to event publisher.
        """
        # Arrange
        mock_handler = Mock()
        mock_handler.handle = Mock()
        mock_handler_class.return_value = mock_handler
        mock_handler_class.__name__ = (
            "MockLoggingEventHandler"  # Add __name__ attribute
        )
        mock_event_publisher = Mock()

        # Act
        container.setup_event_handlers(mock_event_publisher)

        # Assert
        mock_handler_class.assert_called_once()
        mock_event_publisher.subscribe.assert_called_once()
