"""
Rate Limit Decorator

Provides a decorator for applying rate limiting to Flask routes.
Integrates with the rate limiting system to enforce per-IP request limits.
"""

from functools import wraps
from typing import Dict, List, Optional

from flask import current_app, jsonify, make_response, request

from domain.errors import RateLimitExceededError


def rate_limit(
    limit_types: Optional[List[str]] = None,
    custom_limits: Optional[Dict[str, int]] = None
):
    """
    Decorator to apply rate limiting to Flask routes.
    
    This decorator extracts the client IP, checks endpoint-specific rate limits,
    and adds rate limit headers to responses. If a limit is exceeded, it returns
    HTTP 429 with error details.
    
    Args:
        limit_types: Types of limits to apply ('daily', 'hourly', 'per_minute')
                    Currently not used - endpoint limits are configured via environment
        custom_limits: Override default limits for specific types
                      Currently not used - limits are configured via environment
    
    Usage:
        @rate_limit(limit_types=['hourly', 'per_minute'])
        def get_resolutions():
            pass
    
    Requirements: 9.1, 9.2, 9.3, 10.1, 10.2, 10.3, 10.4, 11.1, 11.2, 11.3, 11.4
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get rate limit service from DI container
            rate_limit_service = _get_rate_limit_service()
            
            # Skip rate limiting if service not available
            if not rate_limit_service:
                return f(*args, **kwargs)
            
            # Extract client IP from request
            client_ip = _extract_client_ip(request)
            
            try:
                # Check endpoint-specific limits
                entity = rate_limit_service.check_endpoint_limit(
                    client_ip,
                    request.path
                )
                
                # Execute the route function
                response = make_response(f(*args, **kwargs))
                
                # Add rate limit headers to successful responses (Requirement 10)
                if entity:
                    response.headers.update(entity.to_headers())
                
                return response
                
            except RateLimitExceededError as e:
                # Log rate limit violation (Requirement 9.3)
                current_app.logger.info(
                    f"Rate limit exceeded for {client_ip}: "
                    f"{e.context.get('limit_type', 'unknown')}"
                )
                
                # Return HTTP 429 with headers (Requirement 9.1, 9.2)
                headers = {}
                if e.context:
                    # Try to construct headers from error context
                    if 'limit' in e.context:
                        headers['X-RateLimit-Limit'] = str(e.context['limit'])
                    if 'reset_at' in e.context:
                        from datetime import datetime
                        reset_at = e.context['reset_at']
                        if isinstance(reset_at, str):
                            # Parse ISO format timestamp
                            reset_dt = datetime.fromisoformat(reset_at.replace('Z', '+00:00'))
                            headers['X-RateLimit-Reset'] = str(int(reset_dt.timestamp()))
                        elif isinstance(reset_at, datetime):
                            headers['X-RateLimit-Reset'] = str(int(reset_at.timestamp()))
                    headers['X-RateLimit-Remaining'] = '0'
                
                return jsonify({
                    'error': 'Rate limit exceeded',
                    'limit_type': e.context.get('limit_type') if e.context else None,
                    'reset_at': e.context.get('reset_at') if e.context else None
                }), 429, headers
        
        return decorated_function
    return decorator


def _extract_client_ip(request) -> str:
    """
    Extract client IP from request.
    
    Checks X-Forwarded-For header first (for proxy/load balancer),
    then falls back to remote_addr for direct connections.
    
    Args:
        request: Flask request object
    
    Returns:
        Client IP address as string
    
    Requirements: 11.1, 11.2, 11.3, 11.4
    """
    # Check X-Forwarded-For header (set by proxies/load balancers)
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        # Get first IP in chain (original client)
        # Format: "client, proxy1, proxy2"
        return forwarded_for.split(',')[0].strip()
    
    # Fallback to direct connection IP
    return request.remote_addr or '127.0.0.1'


def _get_rate_limit_service():
    """
    Get rate limit service from DI container.
    
    Returns:
        RateLimitService instance or None if not available
    """
    if not hasattr(current_app, 'container') or current_app.container is None:
        current_app.logger.warning("DI container not available for rate limiting")
        return None
    
    try:
        from application.rate_limit_service import RateLimitService
        return current_app.container.resolve(RateLimitService)
    except Exception as e:
        current_app.logger.warning(f"Rate limit service not available: {e}")
        return None
