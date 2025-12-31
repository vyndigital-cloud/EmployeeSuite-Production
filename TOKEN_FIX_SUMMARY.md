# 401 Unauthorized Error Fix Summary

## Problem
After implementing access token encryption, API calls were returning 401 Unauthorized errors instead of working correctly.

## Root Cause
The token decryption logic had a flaw:
1. It tried to decrypt tokens before checking if they were plaintext
2. If encryption failed (e.g., ENCRYPTION_KEY not set), tokens were stored as plaintext but code tried to decrypt them anyway
3. Decryption would fail and return None, causing 401 errors

## Solution Implemented

### 1. Fixed Token Decryption Logic (`models.py`)
- **Check for plaintext first**: If token starts with `shpat_` or `shpca_`, return it directly (no decryption needed)
- **Only decrypt if needed**: Only attempt decryption if token doesn't look like plaintext
- **Validate decrypted tokens**: Verify decrypted tokens match expected format before returning
- **Better error handling**: Log warnings/errors when decryption fails

### 2. Added Debug Logging (`shopify_integration.py`)
- Log token format when ShopifyClient is initialized
- Warn if token doesn't match expected format (starts with `shpat_` or `shpca_`)
- Error if token is None/empty

### 3. Graceful Encryption Failure Handling (`shopify_oauth.py`, `data_encryption.py`)
- Check if `ENCRYPTION_KEY` is set before attempting encryption
- If encryption fails (returns None), store plaintext token instead (with warning)
- This ensures backwards compatibility if encryption is not configured

## Token Format Validation

Valid Shopify access tokens:
- Start with `shpat_` (private app token) or `shpca_` (OAuth token)
- Length: ~32-40 characters
- Format: `shpat_XXXXXXXXXXXXXXXXXXXXXXXXXXXX`

## Migration Notes

### For Existing Tokens (Plaintext)
- Tokens that are already plaintext will continue to work
- Code detects plaintext format and returns them directly
- No migration needed

### For New Tokens (After Fix)
- If `ENCRYPTION_KEY` is set: Tokens will be encrypted and stored
- If `ENCRYPTION_KEY` is NOT set: Tokens will be stored as plaintext (with warning)
- Decryption automatically handles both formats

## Testing Checklist

1. ✅ Verify tokens starting with `shpat_` are returned as-is (plaintext)
2. ✅ Verify encrypted tokens are decrypted correctly
3. ✅ Verify None/empty tokens return None (not empty string)
4. ✅ Verify debug logging shows token format
5. ✅ Test with ENCRYPTION_KEY set and not set

## Configuration Required

**Set ENCRYPTION_KEY environment variable:**
```bash
ENCRYPTION_KEY=your-base64-encoded-fernet-key-here
```

**To generate a key:**
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Use this as ENCRYPTION_KEY
```

## Status
✅ **FIXED** - Tokens now work correctly whether encrypted or plaintext

