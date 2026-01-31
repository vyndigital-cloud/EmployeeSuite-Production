import logging
import sys
import os
import traceback
import json
from datetime import datetime

# Create comprehensive error log file path
ERROR_LOG_PATH = os.path.join(os.path.dirname(__file__), '.cursor', 'error.log')

def log_comprehensive_error(error_type, error_message, error_location, error_data=None, exc_info=None):
    """
    Log every single error with maximum detail to both console and file
    This captures EVERY crumb of error information possible
    """
    try:
        # Get full stack trace
        stack_trace = ''.join(traceback.format_exception(*exc_info)) if exc_info else traceback.format_exc()
        
        # Build comprehensive error entry
        error_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': str(error_type),
            'error_message': str(error_message),
            'error_location': str(error_location),
            'stack_trace': stack_trace,
            'error_data': error_data or {},
            'system_info': {
                'python_version': sys.version,
                'platform': sys.platform,
                'pid': os.getpid()
            }
        }
        
        # Log to console with full details
        logger = logging.getLogger('employeesuite')
        logger.error(f"[{error_type}] {error_message}")
        logger.error(f"Location: {error_location}")
        logger.error(f"Stack trace:\n{stack_trace}")
        if error_data:
            logger.error(f"Error data: {json.dumps(error_data, indent=2, default=str)}")
        
        # Log to file (NDJSON format for easy parsing)
        os.makedirs(os.path.dirname(ERROR_LOG_PATH), exist_ok=True)
        with open(ERROR_LOG_PATH, 'a') as f:
            f.write(json.dumps(error_entry, default=str) + '\n')
            
    except Exception as e:
        # Even error logging can fail - log to stderr as last resort
        print(f"CRITICAL: Error logging failed: {e}", file=sys.stderr)
        print(f"Original error: {error_type}: {error_message}", file=sys.stderr)

def setup_logging():
    """Configure application logging with comprehensive error capture"""
    # Set up console logging with maximum detail
    logging.basicConfig(
        level=logging.DEBUG,  # Capture everything
        format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
        force=True
    )
    
    # Create logger
    logger = logging.getLogger('employeesuite')
    logger.setLevel(logging.DEBUG)  # Capture all levels
    
    # Also capture warnings
    logging.captureWarnings(True)
    
    return logger

logger = setup_logging()
