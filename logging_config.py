import logging
import sys
import os

def setup_logging():
    """Configure application logging with Sentry integration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Create logger
    logger = logging.getLogger('employeesuite')
    logger.setLevel(logging.INFO)
    
    return logger

logger = setup_logging()
