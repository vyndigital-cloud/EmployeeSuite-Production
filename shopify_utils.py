"""
Shopify Utilities
Centralized logic for safe GID parsing, type conversion, and common helpers.
helps prevent 500 errors from invalid input formats.
"""
from typing import Optional, Union, Any
from logging_config import logger

def parse_gid(gid: Union[str, int, None]) -> Optional[int]:
    """
    Safely extract the numeric ID from a Shopify Global ID (GID).
    
    Args:
        gid: The GID string (e.g. 'gid://shopify/Shop/12345'), numeric string, or int.
        
    Returns:
        int: The numeric ID if successful.
        None: If parsing fails or input is None.
    """
    if gid is None:
        return None
        
    # If it's already an integer, return it
    if isinstance(gid, int):
        return gid
        
    # If it's a string
    if isinstance(gid, str):
        gid = gid.strip()
        if not gid:
            return None
            
        # Try to parse as pure number string
        if gid.isdigit():
            return int(gid)
            
        # Try to parse as GID URI
        if '/' in gid:
            try:
                # take the last part after the slash
                last_part = gid.split('/')[-1]
                # handle potential query params if they exist (though rare in GID)
                clean_id = last_part.split('?')[0]
                if clean_id.isdigit():
                    return int(clean_id)
            except Exception as e:
                logger.warning(f"Failed to parse GID '{gid}': {e}")
                pass
                
    logger.warning(f"Could not parse valid ID from: {gid}")
    return None

def format_gid(numeric_id: Union[str, int], resource_type: str = 'Shop') -> str:
    """
    Format a numeric ID into a Shopify Global ID (GID).
    
    Args:
        numeric_id: The numeric ID.
        resource_type: The Shopify resource type (e.g. 'Shop', 'AppSubscription').
        
    Returns:
        str: The formatted GID.
    """
    return f"gid://shopify/{resource_type}/{numeric_id}"

def safe_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    """
    Safely convert a value to int.
    
    Args:
        value: The value to convert.
        default: The default value to return if conversion fails.
        
    Returns:
        int: The converted integer or default.
    """
    try:
        if value is None:
            return default
        return int(value)
    except (ValueError, TypeError):
        return default
