"""
Data Encryption Utilities for Employee Suite
Encrypts sensitive data at rest
"""
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from logging_config import logger

# Get encryption key from environment or generate one
def get_encryption_key():
    """Get or generate encryption key"""
    key = os.getenv('ENCRYPTION_KEY')
    if not key:
        # Generate a key (in production, set this as environment variable)
        key = Fernet.generate_key().decode()
        logger.warning("ENCRYPTION_KEY not set - using generated key (not secure for production!)")
    else:
        # Convert string key to bytes if needed
        if isinstance(key, str):
            key = key.encode()
    
    return key

def get_cipher():
    """Get Fernet cipher instance"""
    key = get_encryption_key()
    # If key is not 32 bytes, derive it using PBKDF2HMAC
    if len(key) != 44:  # Fernet keys are base64-encoded 32 bytes = 44 chars
        # Derive a proper key from the provided key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'employeesuite_salt_2025',  # In production, use random salt per encryption
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(key if isinstance(key, bytes) else key.encode()))
    else:
        key = key if isinstance(key, bytes) else key.encode()
    
    return Fernet(key)

def encrypt_data(data):
    """Encrypt sensitive data"""
    try:
        if data is None:
            return None
        
        # CRITICAL: Check if ENCRYPTION_KEY is set BEFORE attempting encryption
        # If not set, return None to indicate encryption should be skipped (store plaintext)
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            logger.warning("ENCRYPTION_KEY not set - cannot encrypt data. Returning None to indicate encryption should be skipped.")
            return None
        
        cipher = get_cipher()
        if isinstance(data, str):
            data = data.encode()
        encrypted = cipher.encrypt(data)
        return base64.urlsafe_b64encode(encrypted).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return None

def decrypt_data(encrypted_data):
    """Decrypt sensitive data"""
    try:
        if encrypted_data is None:
            return None
        cipher = get_cipher()
        encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return None

def encrypt_access_token(token):
    """Encrypt Shopify access token"""
    return encrypt_data(token)

def decrypt_access_token(encrypted_token):
    """Decrypt Shopify access token"""
    return decrypt_data(encrypted_token)

def encrypt_user_data(data_dict):
    """Encrypt dictionary of user data"""
    encrypted = {}
    for key, value in data_dict.items():
        if value and isinstance(value, str):
            encrypted[key] = encrypt_data(value)
        else:
            encrypted[key] = value
    return encrypted

def decrypt_user_data(encrypted_dict):
    """Decrypt dictionary of user data"""
    decrypted = {}
    for key, value in encrypted_dict.items():
        if value and isinstance(value, str):
            decrypted[key] = decrypt_data(value)
        else:
            decrypted[key] = value
    return decrypted

