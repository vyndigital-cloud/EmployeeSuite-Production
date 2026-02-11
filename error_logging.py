"""
Bulletproof App-Store-Wide Error Logging System
Captures all errors, API failures, user actions, and system events
"""
import logging
import traceback
import sys
import os
import json
from datetime import datetime, timezone
from functools import wraps
from flask import request, session, g
from logging.handlers import RotatingFileHandler
import threading
from collections import deque
import time

class ErrorLogger:
    """Centralized error logging with multiple outputs and filtering"""
    
    def __init__(self):
        self.error_buffer = deque(maxlen=1000)  # Keep last 1000 errors in memory
        self.lock = threading.Lock()
        self.setup_loggers()
        
    def setup_loggers(self):
        """Setup multiple loggers for different error types"""
        
        # Main error logger
        self.error_logger = logging.getLogger('app_errors')
        self.error_logger.setLevel(logging.DEBUG)
        
        # API error logger
        self.api_logger = logging.getLogger('api_errors')
        self.api_logger.setLevel(logging.DEBUG)
        
        # User action logger
        self.user_logger = logging.getLogger('user_actions')
        self.user_logger.setLevel(logging.INFO)
        
        # System logger
        self.system_logger = logging.getLogger('system_events')
        self.system_logger.setLevel(logging.INFO)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s | '
            'File: %(pathname)s:%(lineno)d | Function: %(funcName)s'
        )
        
        simple_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        )
        
        # Console handler (always visible)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(simple_formatter)
        
        # File handlers with rotation
        try:
            os.makedirs('logs', exist_ok=True)
            
            # Main error log
            error_handler = RotatingFileHandler(
                'logs/app_errors.log', maxBytes=10*1024*1024, backupCount=5
            )
            error_handler.setLevel(logging.DEBUG)
            error_handler.setFormatter(detailed_formatter)
            
            # API error log
            api_handler = RotatingFileHandler(
                'logs/api_errors.log', maxBytes=5*1024*1024, backupCount=3
            )
            api_handler.setLevel(logging.DEBUG)
            api_handler.setFormatter(detailed_formatter)
            
            # User action log
            user_handler = RotatingFileHandler(
                'logs/user_actions.log', maxBytes=5*1024*1024, backupCount=3
            )
            user_handler.setLevel(logging.INFO)
            user_handler.setFormatter(simple_formatter)
            
            # System events log
            system_handler = RotatingFileHandler(
                'logs/system_events.log', maxBytes=5*1024*1024, backupCount=3
            )
            system_handler.setLevel(logging.INFO)
            system_handler.setFormatter(simple_formatter)
            
            # Add handlers to loggers
            for logger in [self.error_logger, self.api_logger, self.user_logger, self.system_logger]:
                logger.addHandler(console_handler)
                
            self.error_logger.addHandler(error_handler)
            self.api_logger.addHandler(api_handler)
            self.user_logger.addHandler(user_handler)
            self.system_logger.addHandler(system_handler)
            
        except Exception as e:
            print(f"Failed to setup file logging: {e}")
            # Fallback to console only
            pass
    
    def get_context_info(self):
        """Get current request context information"""
        context = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'environment': os.getenv('ENVIRONMENT', 'unknown'),
        }
        
        try:
            if request:
                context.update({
                    'url': request.url,
                    'method': request.method,
                    'endpoint': request.endpoint,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', 'Unknown'),
                    # LEVEL 100: Prioritize request.shop_domain populated by identity middleware
                    'shop_domain': getattr(request, 'shop_domain', None) or \
                                  request.headers.get('X-Shopify-Shop-Domain') or \
                                  request.args.get('shop') or \
                                  request.form.get('shop') or \
                                  session.get('shop_domain') or \
                                  session.get('current_shop') or 'None',
                })
                
                # Add user info if available (Prioritize g.current_user from middleware)
                if hasattr(g, 'current_user') and g.current_user:
                    context['user_id'] = getattr(g.current_user, 'id', 'None')
                    context['user_email'] = getattr(g.current_user, 'email', 'Unknown')
                elif session:
                    context['user_id'] = session.get('_user_id', 'None')
                    
                # Stateless verification flag
                context['is_jwt_verified'] = getattr(request, 'session_token_verified', False)
                    
        except Exception:
            # Request context not available
            pass
            
        return context
    
    def log_error(self, error, error_type="GENERAL", additional_context=None):
        """Log an error with full context - optimized"""
        try:
            # Only get context if we're actually going to use it
            context = None
            if additional_context or error_type in ['CRITICAL', 'DATABASE_ERROR', 'STARTUP_ERROR']:
                context = self.get_context_info()
                if additional_context:
                    context.update(additional_context)
            
            # Simplified error info for memory efficiency
            error_info = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error_type': error_type,
                'error_message': str(error)[:500],  # Limit message length
                'error_class': error.__class__.__name__
            }
            
            # Only add full traceback for critical errors
            if error_type in ['CRITICAL', 'DATABASE_ERROR', 'STARTUP_ERROR']:
                error_info['traceback'] = traceback.format_exc()
                
            if context:
                error_info['context'] = context
            
            # Thread-safe buffer update
            with self.lock:
                self.error_buffer.append(error_info)
            
            # Efficient logging message
            if context:
                error_msg = f"[{error_type}] {str(error)[:200]} | Context: {json.dumps(context, default=str)[:300]}"
            else:
                error_msg = f"[{error_type}] {str(error)[:200]}"
            
            # Route to appropriate logger
            if error_type in ['API_ERROR', 'SHOPIFY_ERROR', 'GRAPHQL_ERROR']:
                self.api_logger.error(error_msg)
            else:
                self.error_logger.error(error_msg)
                
            # Console output only for critical errors
            if error_type in ['CRITICAL', 'DATABASE_ERROR', 'STARTUP_ERROR']:
                print(f"🚨 CRITICAL ERROR: {error_msg}")
                
        except Exception as logging_error:
            # Minimal fallback logging
            print(f"ERROR LOGGING FAILED: {logging_error}")
            print(f"ORIGINAL ERROR: {str(error)[:100]}")
            
    def log_api_call(self, endpoint, method, status_code, response_time=None, error=None):
        """Log API calls and responses"""
        try:
            context = self.get_context_info()
            
            log_msg = f"API Call: {method} {endpoint} -> {status_code}"
            if response_time:
                log_msg += f" ({response_time:.2f}ms)"
            if error:
                log_msg += f" | Error: {error}"
                
            if status_code >= 400:
                self.api_logger.error(log_msg)
            else:
                self.api_logger.info(log_msg)
                
        except Exception as e:
            print(f"Failed to log API call: {e}")
    
    def log_user_action(self, action, user_id=None, details=None):
        """Log user actions for debugging"""
        try:
            context = self.get_context_info()
            
            # Ensure shop_domain is present even if request context is limited
            if details:
                context.update(details)
            
            # HEALTH CHECK SILENCING: Skip UptimeRobot or generic HEAD health checks
            user_agent = request.headers.get('User-Agent', '') if request else ''
            if 'UptimeRobot' in user_agent or (request and request.method == 'HEAD'):
                return

            # [SECURITY AUDIT] Check for discrepancies (non-blocking by default)
            try:
                from security_audit import audit_security_discrepancies
                audit_security_discrepancies(context)
            except ImportError:
                pass  # security_audit module not available
            except Exception as audit_error:
                # Don't let audit failures break logging
                self.error_logger.debug(f"Security audit check failed: {audit_error}")

            log_msg = f"User Action: {action}"
            if user_id:
                log_msg += f" | User: {user_id}"
            
            # Include shop_domain explicitly in the simple message for easier monitoring
            shop = context.get('shop_domain', 'None')
            log_msg += f" | Shop: {shop}"
            
            if context:
                log_msg += f" | Details: {json.dumps(context, default=str)}"
                
            self.user_logger.info(log_msg)
            
        except Exception as e:
            print(f"Failed to log user action: {e}")
    
    def log_system_event(self, event, details=None):
        """Log system events"""
        try:
            log_msg = f"System Event: {event}"
            if details:
                log_msg += f" | Details: {json.dumps(details, default=str)}"
                
            self.system_logger.info(log_msg)
            
        except Exception as e:
            print(f"Failed to log system event: {e}")
    
    def get_recent_errors(self, count=50):
        """Get recent errors from memory buffer"""
        with self.lock:
            return list(self.error_buffer)[-count:]

# Global error logger instance
error_logger = ErrorLogger()

def log_errors(error_type="GENERAL"):
    """Decorator to automatically log function errors"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_logger.log_error(
                    e, 
                    error_type=error_type,
                    additional_context={
                        'function': func.__name__,
                        'args': str(args)[:200],  # Limit length
                        'kwargs': str(kwargs)[:200]
                    }
                )
                raise  # Re-raise the error
        return wrapper
    return decorator

def safe_execute(func, error_type="GENERAL", default_return=None):
    """Safely execute a function and log any errors"""
    try:
        return func()
    except Exception as e:
        error_logger.log_error(e, error_type=error_type)
        return default_return
