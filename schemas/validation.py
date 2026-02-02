"""
Simplified validation for production deployment
"""

from typing import Any, Dict


class APIRequestSchema:
    def __init__(self, **kwargs):
        self.shop = kwargs.get("shop")
        self.host = kwargs.get("host")
        self.user_id = kwargs.get("user_id")


class APIResponseSchema:
    def __init__(self, **kwargs):
        self.success = kwargs.get("success", False)
        self.message = kwargs.get("message")
        self.error = kwargs.get("error")
        self.data = kwargs.get("data")
        self.action = kwargs.get("action")

    def dict(self):
        return {
            "success": self.success,
            "message": self.message,
            "error": self.error,
            "data": self.data,
            "action": self.action,
        }


def validate_request(schema_class, data: Dict[str, Any]):
    """Simple request validation"""
    try:
        return schema_class(**data)
    except Exception as e:
        raise ValueError(f"Validation failed: {str(e)}")


def validate_response(data: Dict[str, Any]):
    """Simple response validation"""
    try:
        return APIResponseSchema(**data)
    except Exception:
        return APIResponseSchema(success=False, error="Response validation failed")
