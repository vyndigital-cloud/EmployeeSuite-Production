"""
Data Encryption Utilities for MissionControl
Provides secure encryption/decryption for sensitive data at rest
"""

import base64
import hashlib
import logging
import os
from typing import Optional, Union

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger("missioncontrol.encryption")


class EncryptionError(Exception):
    """Custom exception for encryption-related errors"""

    pass


class EncryptionManager:
    """Manages encryption and decryption operations"""

    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption manager with environment key priority"""
        # Priority: 1. Passed key, 2. Environment variable, 3. None
        self.encryption_key = (
            encryption_key
            or os.getenv("ENCRYPTION_KEY")
            or os.getenv("SECRET_KEY")  # Fallback to SECRET_KEY
        )

        if self.encryption_key:
            logger.info("Encryption manager initialized with key")
        else:
            logger.warning("No encryption key available - encryption disabled")

        self._cipher = None
        self._validate_setup()

    def _validate_setup(self) -> None:
        """Validate encryption setup"""
        if not self.encryption_key:
            logger.warning(
                "No encryption key provided - encryption will be disabled. "
                "Set ENCRYPTION_KEY environment variable for production use."
            )
            return

        if len(self.encryption_key) < 32:
            raise EncryptionError("Encryption key must be at least 32 characters long")

    def _get_cipher(self) -> Optional[Fernet]:
        """Get or create Fernet cipher instance"""
        if not self.encryption_key:
            return None

        if self._cipher is None:
            try:
                key = self._derive_key(self.encryption_key)
                self._cipher = Fernet(key)
            except Exception as e:
                logger.error(f"Failed to create cipher: {e}")
                raise EncryptionError(f"Cipher initialization failed: {e}")

        return self._cipher

    def _derive_key(self, password: str) -> bytes:
        """Derive a proper Fernet key from password using PBKDF2"""
        # Use a fixed salt for key derivation (in production, consider per-app salts)
        salt = b"missioncontrol_2025_salt"

        # Use PBKDF2 to derive a proper 32-byte key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # 100k iterations for security
        )

        password_bytes = password.encode() if isinstance(password, str) else password
        derived_key = kdf.derive(password_bytes)

        # Return base64-encoded key for Fernet
        return base64.urlsafe_b64encode(derived_key)

    def is_encryption_available(self) -> bool:
        """Check if encryption is available and properly configured"""
        try:
            return self._get_cipher() is not None
        except EncryptionError:
            return False

    def encrypt(self, data: Union[str, bytes]) -> Optional[str]:
        """
        Encrypt data and return base64-encoded string

        Args:
            data: Data to encrypt (string or bytes)

        Returns:
            Base64-encoded encrypted data, or None if encryption failed
        """
        if not data:
            return None

        cipher = self._get_cipher()
        if cipher is None:
            logger.debug("Encryption not available - returning None")
            return None

        try:
            # Convert string to bytes if needed
            if isinstance(data, str):
                data_bytes = data.encode("utf-8")
            else:
                data_bytes = data

            # Encrypt the data
            encrypted = cipher.encrypt(data_bytes)

            # Return base64-encoded string for storage
            result = base64.urlsafe_b64encode(encrypted).decode("ascii")

            logger.debug(f"Successfully encrypted data (length: {len(result)})")
            return result

        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            return None

    def decrypt(self, encrypted_data: str) -> Optional[str]:
        """Decrypt data with graceful failure handling"""
        if not encrypted_data or not self.is_encryption_available():
            return encrypted_data  # Return as-is if no encryption

        try:
            # Check if data is actually encrypted
            if not self.is_encrypted(encrypted_data):
                return encrypted_data  # Return plain text as-is

            cipher = self._get_cipher()
            if not cipher:
                logger.warning("Cipher not available for decryption")
                return None  # Graceful failure

            # Decode from base64 and decrypt
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode("ascii"))
            decrypted_bytes = cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode("utf-8")

        except Exception as e:
            logger.warning(f"Decryption failed - invalid token: {e}")
            return None  # GRACEFUL FAILURE - don't crash

    def is_encrypted(self, data: str) -> bool:
        """
        Check if data appears to be encrypted by this system

        Args:
            data: Data to check

        Returns:
            True if data appears to be encrypted
        """
        if not data or len(data) < 50:  # Encrypted data should be longer
            return False

        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(data.encode("ascii"))

            # If we can decode it and it's long enough, likely encrypted
            # (This is a heuristic, not perfect)
            return True

        except Exception:
            return False


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get global encryption manager instance"""
    global _encryption_manager

    if _encryption_manager is None:
        _encryption_manager = EncryptionManager()

    return _encryption_manager


def is_encryption_available() -> bool:
    """Check if encryption is available"""
    return get_encryption_manager().is_encryption_available()


def encrypt_data(data: Union[str, bytes]) -> Optional[str]:
    """
    Encrypt data using the global encryption manager

    Args:
        data: Data to encrypt

    Returns:
        Encrypted data as base64 string, or None if encryption failed
    """
    return get_encryption_manager().encrypt(data)


def decrypt_data(encrypted_data: str) -> Optional[str]:
    """
    Decrypt data using the global encryption manager

    Args:
        encrypted_data: Base64-encoded encrypted data

    Returns:
        Decrypted string, or None if decryption failed
    """
    return get_encryption_manager().decrypt(encrypted_data)


def encrypt_access_token(token: str) -> Optional[str]:
    """
    Encrypt a Shopify access token

    Args:
        token: Access token to encrypt

    Returns:
        Encrypted token, or None if encryption failed
    """
    if not token:
        return None

    # Validate token format before encryption
    if not (token.startswith("shpat_") or token.startswith("shpca_")):
        logger.warning(f"Token doesn't match expected Shopify format: {token[:10]}...")

    return encrypt_data(token)


def decrypt_access_token(encrypted_token: str) -> Optional[str]:
    """
    Decrypt a Shopify access token

    Args:
        encrypted_token: Encrypted token to decrypt

    Returns:
        Decrypted token, or None if decryption failed
    """
    if not encrypted_token:
        return None

    # If token already looks like a plaintext Shopify token, return as-is
    if encrypted_token.startswith("shpat_") or encrypted_token.startswith("shpca_"):
        logger.debug("Token appears to be plaintext, returning as-is")
        return encrypted_token

    # Try to decrypt
    decrypted = decrypt_data(encrypted_token)

    if decrypted:
        # Validate decrypted token format
        if not (decrypted.startswith("shpat_") or decrypted.startswith("shpca_")):
            logger.warning(
                f"Decrypted token doesn't match expected format: {decrypted[:10]}..."
            )

        return decrypted

    return None


def encrypt_user_data(data_dict: dict) -> dict:
    """
    Encrypt sensitive fields in a user data dictionary

    Args:
        data_dict: Dictionary containing user data

    Returns:
        Dictionary with encrypted sensitive fields
    """
    if not data_dict or not isinstance(data_dict, dict):
        return data_dict

    # Define fields that should be encrypted
    sensitive_fields = {
        "access_token",
        "refresh_token",
        "password",
        "api_key",
        "secret",
        "private_key",
    }

    encrypted_dict = {}

    for key, value in data_dict.items():
        if key.lower() in sensitive_fields and isinstance(value, str) and value:
            # Encrypt sensitive field
            encrypted_value = encrypt_data(value)
            encrypted_dict[key] = encrypted_value if encrypted_value else value
        else:
            # Keep non-sensitive fields as-is
            encrypted_dict[key] = value

    return encrypted_dict


def decrypt_user_data(encrypted_dict: dict) -> dict:
    """
    Decrypt sensitive fields in an encrypted user data dictionary

    Args:
        encrypted_dict: Dictionary with encrypted sensitive fields

    Returns:
        Dictionary with decrypted sensitive fields
    """
    if not encrypted_dict or not isinstance(encrypted_dict, dict):
        return encrypted_dict

    # Define fields that might be encrypted
    sensitive_fields = {
        "access_token",
        "refresh_token",
        "password",
        "api_key",
        "secret",
        "private_key",
    }

    decrypted_dict = {}

    for key, value in encrypted_dict.items():
        if key.lower() in sensitive_fields and isinstance(value, str) and value:
            # Try to decrypt sensitive field
            decrypted_value = decrypt_data(value)
            decrypted_dict[key] = decrypted_value if decrypted_value else value
        else:
            # Keep non-sensitive fields as-is
            decrypted_dict[key] = value

    return decrypted_dict


def generate_encryption_key() -> str:
    """
    Generate a new encryption key suitable for use with this system

    Returns:
        Base64-encoded encryption key
    """
    key = Fernet.generate_key()
    return key.decode("ascii")


def validate_encryption_key(key: str) -> bool:
    """
    Validate that an encryption key is suitable for use

    Args:
        key: Encryption key to validate

    Returns:
        True if key is valid
    """
    if not key or len(key) < 32:
        return False

    try:
        # Try to create an encryption manager with this key
        manager = EncryptionManager(key)
        return manager.is_encryption_available()
    except EncryptionError:
        return False


# Initialize logging for this module
logger.info(f"Encryption module loaded - Available: {is_encryption_available()}")
