from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timedelta
from sqlalchemy.orm import validates

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trial_ends_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    is_subscribed = db.Column(db.Boolean, default=False)
    stripe_customer_id = db.Column(db.String(255), nullable=True, index=True)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    shopify_stores = db.relationship('ShopifyStore', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def is_trial_active(self):
        return datetime.utcnow() < self.trial_ends_at and not self.is_subscribed
    
    def has_access(self):
        return self.is_subscribed or self.is_trial_active()
    
    def __repr__(self):
        return f'<User {self.email}>'

class ShopifyStore(db.Model):
    __tablename__ = 'shopify_stores'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    shop_url = db.Column(db.String(255), nullable=False, index=True)
    shop_id = db.Column(db.BigInteger, nullable=True, index=True)  # Shopify shop ID
    access_token = db.Column(db.String(255), nullable=False)
    charge_id = db.Column(db.String(255), nullable=True, index=True)  # Shopify charge ID for billing
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    uninstalled_at = db.Column(db.DateTime, nullable=True)  # When app was uninstalled
    
    @validates('access_token')
    def validate_access_token(self, key, value):
        """Validate access_token before setting - prevent None values"""
        if value is None:
            # Convert None to empty string to satisfy NOT NULL constraint
            return ''
        if not isinstance(value, str):
            raise ValueError(f"access_token must be a string, got {type(value)}")
        return value
    
    def disconnect(self):
        """Disconnect store - clears token and marks inactive. Centralized state management."""
        self.access_token = ''  # Use empty string (NOT NULL constraint)
        self.is_active = False
        self.charge_id = None
        self.uninstalled_at = datetime.utcnow()
    
    def is_connected(self):
        """Check if store is properly connected (has valid token and is active)"""
        return self.is_active and bool(self.access_token and self.access_token.strip())
    
    def get_access_token(self):
        """Get access token, returning None if empty/invalid (for validation checks)"""
        token = self.access_token
        if not token or not token.strip():
            return None
        return token
    
    def __repr__(self):
        return f'<ShopifyStore {self.shop_url}>'
