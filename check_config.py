
import os
import sys
from dotenv import load_dotenv

load_dotenv()

REQUIRED_KEYS = [
    "SHOPIFY_API_KEY",
    "SHOPIFY_API_SECRET",
    "DATABASE_URL",
    "SECRET_KEY",
    "MAIL_USERNAME",
    "MAIL_PASSWORD"
]

print("--- CONFIGURATION DIAGNOSTIC ---")
missing = []
for key in REQUIRED_KEYS:
    value = os.getenv(key)
    if not value:
        print(f"❌ MISSING: {key}")
        missing.append(key)
    else:
        # Mask sensitive values
        masked = value[:4] + "*" * 4 if len(value) > 4 else "*" * len(value)
        print(f"✅ FOUND:   {key} = {masked}")

if missing:
    print(f"\nCRITICAL: {len(missing)} missing configuration keys.")
    sys.exit(1)
else:
    print("\nSUCCESS: All required configuration keys are present.")
    sys.exit(0)
