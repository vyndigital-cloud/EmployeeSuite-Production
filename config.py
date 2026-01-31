import os

# Shopify API Version - Centralized for easy updates
# Default to 2025-10 as found in the codebase
SHOPIFY_API_VERSION = os.getenv('SHOPIFY_API_VERSION', '2025-10')

# Environment flags
DEBUG_MODE = os.getenv('DEBUG', 'False').lower() == 'true'
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
