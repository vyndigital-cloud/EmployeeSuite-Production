"""
Strict Schema Enforcement - No loose dictionaries allowed
Every request/response must pass through validation
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator, root_validator
from enum import Enum

class RequestStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"

class ShopifyStoreSchema(BaseModel):
    shop_url: str = Field(..., regex=r'^[a-zA-Z0-9\-]+\.myshopify\.com$')
    access_token: Optional[str] = Field(None, min_length=20)
    is_active: bool = True
    
    @validator('shop_url')
    def validate_shop_url(cls, v):
        if not v.endswith('.myshopify.com'):
            raise ValueError('Shop URL must end with .myshopify.com')
        return v.lower()

class UserSchema(BaseModel):
    id: Optional[int] = None
    email: str = Field(..., regex=r'^[^@]+@[^@]+\.[^@]+$')
    is_subscribed: bool = False
    trial_ends_at: Optional[datetime] = None
    
    @validator('email')
    def validate_email(cls, v):
        return v.lower().strip()

class APIRequestSchema(BaseModel):
    shop: Optional[str] = None
    host: Optional[str] = None
    user_id: Optional[int] = None
    
    @validator('shop')
    def validate_shop(cls, v):
        if v and not v.endswith('.myshopify.com'):
            if '.' not in v:
                return f"{v}.myshopify.com"
        return v

class APIResponseSchema(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    action: Optional[str] = None
    
    @root_validator
    def validate_response(cls, values):
        success = values.get('success')
        error = values.get('error')
        message = values.get('message')
        
        if success and error:
            raise ValueError('Cannot have both success=True and error message')
        if not success and not error:
            raise ValueError('Failed responses must include error message')
        if success and not message and not values.get('data'):
            raise ValueError('Successful responses must include message or data')
        
        return values

class InventoryItemSchema(BaseModel):
    product: str = Field(..., min_length=1)
    sku: str = Field(..., min_length=1)
    stock: int = Field(..., ge=0)
    price: str = Field(..., regex=r'^\$?\d+\.?\d*$')

class OrderSchema(BaseModel):
    id: Union[str, int]
    customer: str
    total: str = Field(..., regex=r'^\$\d+\.?\d*$')
    items: int = Field(..., ge=0)
    status: str

def validate_request(schema_class: BaseModel, data: Dict[str, Any]) -> BaseModel:
    """Validate incoming request data against schema"""
    try:
        return schema_class(**data)
    except Exception as e:
        raise ValueError(f"Schema validation failed: {str(e)}")

def validate_response(data: Dict[str, Any]) -> APIResponseSchema:
    """Validate outgoing response data"""
    try:
        return APIResponseSchema(**data)
    except Exception as e:
        # Return a valid error response if validation fails
        return APIResponseSchema(
            success=False,
            error=f"Response validation failed: {str(e)}"
        )
