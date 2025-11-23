"""
Test Application Factory

Demonstrates how the factory pattern improves testability by allowing
configuration overrides and dependency injection.
"""

import unittest
from app_factory import create_app, AppConfig


class TestAppFactory(unittest.TestCase):
    """Test application factory pattern."""
    
    def test_create_app_with_default_config(self):
        """Test creating app with default configuration."""
        app = create_app()
        
        # Verify app is created
        self.assertIsNotNone(app)
        self.assertEqual(app.name, "app_factory")
        
        # Verify services are attached
        self.assertTrue(hasattr(app, 'job_service'))
        self.assertTrue(hasattr(app, 'file_manager'))
        self.assertTrue(hasattr(app, 'signed_url_service'))
        self.assertTrue(hasattr(app, 'celery'))
        self.assertTrue(hasattr(app, 'limiter'))
        
        # Verify dependency container is attached
        self.assertTrue(hasattr(app, 'container'))
        self.assertIsNotNone(app.container)
    
    def test_create_app_with_custom_config(self):
        """Test creating app with custom configuration."""
        config = AppConfig()
        config.api_version = "v2"
        config.is_production = False
        config.socketio_enabled = False
        
        app = create_app(config)
        
        # Verify app is created with custom config
        self.assertIsNotNone(app)
        
        # Verify rate limiting is disabled in non-production
        self.assertFalse(app.limiter.enabled)
    
    def test_app_has_health_endpoint(self):
        """Test that health endpoint is registered."""
        app = create_app()
        
        with app.test_client() as client:
            response = client.get('/health')
            self.assertEqual(response.status_code, 200)
            
            data = response.get_json()
            self.assertIn('status', data)
            self.assertIn('redis', data)
            self.assertIn('celery', data)
    
    def test_app_has_api_blueprint(self):
        """Test that API blueprint is registered."""
        app = create_app()
        
        # Check that API routes are registered
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertTrue(any('/api/v1' in rule for rule in rules))
    
    def test_multiple_app_instances(self):
        """Test creating multiple independent app instances."""
        app1 = create_app()
        app2 = create_app()
        
        # Verify both apps are created
        self.assertIsNotNone(app1)
        self.assertIsNotNone(app2)
        
        # Verify they are independent instances
        self.assertIsNot(app1, app2)


if __name__ == '__main__':
    unittest.main()
