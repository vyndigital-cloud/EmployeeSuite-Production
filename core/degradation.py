"""
Graceful Degradation - Keep core UI alive even when services fail
"""
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class ServiceStatus:
    def __init__(self):
        self.services = {}
        self.last_check = {}
    
    def mark_service_down(self, service_name: str, error: str):
        """Mark a service as down"""
        self.services[service_name] = {
            'status': 'down',
            'error': error,
            'timestamp': datetime.utcnow()
        }
        logger.warning(f"Service {service_name} marked as DOWN: {error}")
    
    def mark_service_up(self, service_name: str):
        """Mark a service as up"""
        was_down = self.services.get(service_name, {}).get('status') == 'down'
        self.services[service_name] = {
            'status': 'up',
            'timestamp': datetime.utcnow()
        }
        if was_down:
            logger.info(f"Service {service_name} recovered")
    
    def is_service_down(self, service_name: str) -> bool:
        """Check if service is marked as down"""
        service = self.services.get(service_name, {})
        return service.get('status') == 'down'
    
    def get_fallback_data(self, service_name: str) -> Dict[str, Any]:
        """Get fallback data for a down service"""
        fallbacks = {
            'database': {
                'user': {'has_access': True, 'is_trial_active': True, 'days_left': 7},
                'store': {'is_connected': False}
            },
            'shopify': {
                'orders': [],
                'inventory': [],
                'message': 'Shopify API temporarily unavailable. Please try again in a few minutes.'
            }
        }
        return fallbacks.get(service_name, {})

# Global service status tracker
service_status = ServiceStatus()

def with_graceful_degradation(service_name: str, fallback_data: Optional[Dict] = None):
    """Decorator for graceful degradation"""
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # If service is known to be down, return fallback immediately
                if service_status.is_service_down(service_name):
                    logger.info(f"Using fallback for {service_name} (service down)")
                    return _create_fallback_response(service_name, fallback_data)
                
                # Try the actual function
                result = func(*args, **kwargs)
                service_status.mark_service_up(service_name)
                return result
                
            except Exception as e:
                logger.error(f"Service {service_name} failed: {str(e)}")
                service_status.mark_service_down(service_name, str(e))
                return _create_fallback_response(service_name, fallback_data, str(e))
        
        return wrapper
    return decorator

def _create_fallback_response(service_name: str, fallback_data: Optional[Dict], error: str = None) -> Dict[str, Any]:
    """Create a fallback response when service is down"""
    base_response = {
        'success': False,
        'error': f'{service_name.title()} service temporarily unavailable',
        'fallback': True,
        'action': 'retry'
    }
    
    # Add service-specific fallback data
    if fallback_data:
        base_response.update(fallback_data)
    else:
        base_response.update(service_status.get_fallback_data(service_name))
    
    # For UI endpoints, provide user-friendly messages
    if service_name == 'shopify':
        base_response['html'] = '''
        <div style="padding: 20px; background: #fffbf0; border: 1px solid #fef3c7; border-radius: 8px;">
            <h3 style="color: #92400e; margin-bottom: 8px;">⚠️ Shopify Temporarily Unavailable</h3>
            <p style="color: #6d7175;">We're having trouble connecting to Shopify right now. This usually resolves within a few minutes.</p>
            <button onclick="location.reload()" style="margin-top: 12px; padding: 8px 16px; background: #008060; color: white; border: none; border-radius: 6px; cursor: pointer;">Try Again</button>
        </div>
        '''
    
    return base_response
