"""
Performance tests for UltraDL API endpoints.

Tests verify that critical API endpoints meet the 200ms p95 latency requirement
by measuring response times across 100 requests per endpoint.

Note: These tests measure API overhead only, not external service latency (YouTube API).

Requirements: 10.1, 10.2, 10.3, 10.4, 10.5
"""

import json
import os
import sys
import time
from typing import List, Dict

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Set up environment for testing
if 'REDIS_URL' not in os.environ:
    os.environ['REDIS_URL'] = 'redis://redis:6379/0'

from main import app as main_app


# Fixtures for performance measurement
@pytest.fixture
def perf_client():
    """Create Flask test client for performance testing."""
    app = main_app
    app.config['TESTING'] = True
    return app.test_client()


@pytest.fixture
def perf_metrics():
    """Fixture to store and calculate performance metrics."""
    def calculate_percentiles(latencies: List[float]) -> Dict[str, float]:
        """Calculate p50, p95, p99 percentiles from latency list.
        
        Args:
            latencies: List of latency measurements in milliseconds
            
        Returns:
            Dictionary with p50, p95, p99 values
        """
        if not latencies:
            return {'p50': 0.0, 'p95': 0.0, 'p99': 0.0, 'mean': 0.0, 'min': 0.0, 'max': 0.0}
        
        sorted_latencies = sorted(latencies)
        n = len(sorted_latencies)
        
        def percentile(p: float) -> float:
            k = (n - 1) * p
            f = int(k)
            c = f + 1
            if c >= n:
                return sorted_latencies[-1]
            d0 = sorted_latencies[f] * (c - k)
            d1 = sorted_latencies[c] * (k - f)
            return d0 + d1
        
        return {
            'p50': percentile(0.50),
            'p95': percentile(0.95),
            'p99': percentile(0.99),
            'mean': sum(latencies) / n,
            'min': min(latencies),
            'max': max(latencies)
        }
    
    return calculate_percentiles


@pytest.fixture
def sample_job_id(perf_client):
    """Create a sample job for performance testing.
    
    Returns:
        Job ID string
    """
    # Use the app's job_service directly
    app = main_app
    job_service = app.job_service
    
    job_data = job_service.create_download_job(
        url="https://www.youtube.com/watch?v=test_perf",
        format_id="18"
    )
    
    yield job_data['job_id']
    
    # Cleanup
    try:
        job_service.delete_job(job_data['job_id'])
    except:
        pass


# Performance test marker
pytestmark = pytest.mark.performance


class TestAPIPerformance:
    """Performance tests for API endpoints (Requirement 10.1, 10.2, 10.3, 10.4)."""
    
    def test_get_job_status_p95_under_200ms(self, perf_client, perf_metrics, sample_job_id):
        """Test GET /api/v1/jobs/{job_id} p95 < 200ms (Requirement 10.2, 10.3, 10.4).
        
        Measures latency across 100 requests and verifies p95 latency is under 200ms.
        """
        print("\n=== Performance Test: GET /jobs/{job_id} ===")
        
        latencies = []
        num_requests = 100
        
        # Warm-up request
        perf_client.get(f"/api/v1/jobs/{sample_job_id}")
        
        # Measure latency for 100 requests
        for i in range(num_requests):
            start = time.time()
            response = perf_client.get(f"/api/v1/jobs/{sample_job_id}")
            latency = (time.time() - start) * 1000  # Convert to milliseconds
            latencies.append(latency)
            
            assert response.status_code == 200, f"Request {i+1} failed with status {response.status_code}"
        
        # Calculate metrics
        metrics = perf_metrics(latencies)
        
        print(f"\nLatency Metrics (ms):"
              f"\n  Mean:  {metrics['mean']:.2f}"
              f"\n  Min:   {metrics['min']:.2f}"
              f"\n  Max:   {metrics['max']:.2f}"
              f"\n  p50:   {metrics['p50']:.2f}"
              f"\n  p95:   {metrics['p95']:.2f}"
              f"\n  p99:   {metrics['p99']:.2f}")
        
        # Verify p95 latency requirement
        assert metrics['p95'] < 200, \
            f"p95 latency {metrics['p95']:.2f}ms exceeds 200ms threshold"
        
        print(f"\n✓ p95 latency {metrics['p95']:.2f}ms is under 200ms threshold")
    
    def test_post_downloads_p95_under_200ms(self, perf_client, perf_metrics):
        """Test POST /api/v1/downloads/ p95 < 200ms (Requirement 10.2, 10.3, 10.4).
        
        Measures latency across 100 requests and verifies p95 latency is under 200ms.
        Note: Measures API overhead only, not actual download processing time.
        """
        print("\n=== Performance Test: POST /downloads/ ===")
        
        latencies = []
        num_requests = 100
        
        payload = {
            "url": "https://www.youtube.com/watch?v=perf_test_download",
            "format_id": "18"
        }
        
        # Warm-up request
        perf_client.post(
            "/api/v1/downloads/",
            data=json.dumps(payload),
            content_type="application/json"
        )
        
        # Measure latency for 100 requests
        for i in range(num_requests):
            start = time.time()
            response = perf_client.post(
                "/api/v1/downloads/",
                data=json.dumps(payload),
                content_type="application/json"
            )
            latency = (time.time() - start) * 1000  # Convert to milliseconds
            latencies.append(latency)
            
            # Accept 202 (accepted) as valid response
            assert response.status_code == 202, \
                f"Request {i+1} failed with unexpected status {response.status_code}"
        
        # Calculate metrics
        metrics = perf_metrics(latencies)
        
        print(f"\nLatency Metrics (ms):"
              f"\n  Mean:  {metrics['mean']:.2f}"
              f"\n  Min:   {metrics['min']:.2f}"
              f"\n  Max:   {metrics['max']:.2f}"
              f"\n  p50:   {metrics['p50']:.2f}"
              f"\n  p95:   {metrics['p95']:.2f}"
              f"\n  p99:   {metrics['p99']:.2f}")
        
        # Verify p95 latency requirement
        assert metrics['p95'] < 200, \
            f"p95 latency {metrics['p95']:.2f}ms exceeds 200ms threshold"
        
        print(f"\n✓ p95 latency {metrics['p95']:.2f}ms is under 200ms threshold")
    
    def test_all_endpoints_latency_summary(self, perf_client, perf_metrics, sample_job_id):
        """Test all critical endpoints and provide summary (Requirement 10.2, 10.3, 10.4).
        
        Runs a smaller set of requests (20 per endpoint) and provides a summary
        of latency metrics across all critical API endpoints.
        """
        print("\n=== Performance Summary: All Critical Endpoints ===")
        
        num_requests = 20
        endpoints = []
        
        # Test 1: GET /jobs/{job_id}
        latencies_job = []
        for _ in range(num_requests):
            start = time.time()
            response = perf_client.get(f"/api/v1/jobs/{sample_job_id}")
            latency = (time.time() - start) * 1000
            latencies_job.append(latency)
            assert response.status_code == 200
        
        metrics_job = perf_metrics(latencies_job)
        endpoints.append(('GET /jobs/{job_id}', metrics_job))
        
        # Test 2: POST /downloads/
        latencies_downloads = []
        payload_downloads = {"url": "https://www.youtube.com/watch?v=summary_test", "format_id": "18"}
        for _ in range(num_requests):
            start = time.time()
            response = perf_client.post(
                "/api/v1/downloads/",
                data=json.dumps(payload_downloads),
                content_type="application/json"
            )
            latency = (time.time() - start) * 1000
            latencies_downloads.append(latency)
            assert response.status_code == 202
        
        metrics_downloads = perf_metrics(latencies_downloads)
        endpoints.append(('POST /downloads/', metrics_downloads))
        
        # Print summary table
        print(f"\n{'Endpoint':<30} {'Mean':<10} {'p50':<10} {'p95':<10} {'p99':<10} {'Status'}")
        print("-" * 90)
        
        all_pass = True
        for endpoint_name, metrics in endpoints:
            status = "✓ PASS" if metrics['p95'] < 200 else "✗ FAIL"
            if metrics['p95'] >= 200:
                all_pass = False
            
            print(f"{endpoint_name:<30} "
                  f"{metrics['mean']:>8.2f}ms "
                  f"{metrics['p50']:>8.2f}ms "
                  f"{metrics['p95']:>8.2f}ms "
                  f"{metrics['p99']:>8.2f}ms "
                  f"{status}")
        
        print("\n" + "=" * 90)
        
        if all_pass:
            print("✓ All endpoints meet p95 < 200ms requirement")
        else:
            print("✗ Some endpoints exceed p95 200ms threshold")
        
        assert all_pass, "One or more endpoints failed to meet p95 < 200ms requirement"


if __name__ == "__main__":
    # Run performance tests
    pytest.main([__file__, "-v", "-s", "-m", "performance"])
