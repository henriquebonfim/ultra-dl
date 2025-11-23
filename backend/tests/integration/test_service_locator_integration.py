"""
Integration test for DependencyContainer with real app.
"""

from app_factory import create_app
from application.download_service import DownloadService
from application.job_service import JobService
from application.video_service import VideoService

print('=== DependencyContainer Integration Test ===\n')

# Create app
app = create_app()
print('✓ App created successfully\n')

# Test service retrieval within app context
with app.app_context():
    ds = app.container.resolve(DownloadService)
    js = app.container.resolve(JobService)
    vs = app.container.resolve(VideoService)
    
    print('✓ All services retrieved successfully:')
    print(f'  - DownloadService: {type(ds).__name__}')
    print(f'  - JobService: {type(js).__name__}')
    print(f'  - VideoService: {type(vs).__name__}')
    print(f'\n✓ Container has {len(app.container._singletons)} registered services')

print('\n=== Integration Test PASSED ===')
