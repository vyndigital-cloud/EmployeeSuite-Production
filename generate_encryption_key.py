#!/usr/bin/env python3
"""
Generate Encryption Key for Employee Suite
Run this script to generate a secure encryption key
"""
from cryptography.fernet import Fernet

def generate_key():
    """Generate a new encryption key"""
    key = Fernet.generate_key()
    print("=" * 60)
    print("ENCRYPTION KEY GENERATED")
    print("=" * 60)
    print(f"\nAdd this to your .env file or environment variables:\n")
    print(f"ENCRYPTION_KEY={key.decode()}\n")
    print("=" * 60)
    print("\n⚠️  IMPORTANT:")
    print("- Keep this key secure and never commit it to version control")
    print("- If you lose this key, encrypted data cannot be decrypted")
    print("- Use the same key in all environments (dev, staging, production)")
    print("=" * 60)
    return key.decode()

if __name__ == '__main__':
    generate_key()

