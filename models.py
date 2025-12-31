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
    trial_ends_at = db.Column(db.DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))  # 7-day free trial
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
    is_active = db.Column(db.Boolean, default=True, index=True)  # Added index for composite queries
    uninstalled_at = db.Column(db.DateTime, nullable=True)  # When app was uninstalled
    
    # Composite index for common query pattern: filter_by(shop_url=shop, is_active=True)
    __table_args__ = (
        db.Index('idx_shopify_store_shop_active', 'shop_url', 'is_active'),
        db.Index('idx_shopify_store_user_active', 'user_id', 'is_active'),
    )
    
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
        """Get access token, decrypting if encrypted, returning None if empty/invalid"""
        token = self.access_token
        if not token or not token.strip():
            # #region agent log
            try:
                import json
                import time
                with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"models.py:get_access_token","message":"Token is empty or None","data":{"shop_url":self.shop_url if hasattr(self,'shop_url') else "unknown"},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
            return None
        
        # #region agent log
        try:
            import json
            import time
            with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"models.py:get_access_token","message":"Token retrieved from DB","data":{"token_length":len(token),"token_starts_with_shpat":token.startswith('shpat_') if token else False,"token_starts_with_shpca":token.startswith('shpca_') if token else False,"token_preview":token[:20] if token and len(token) > 20 else token},"timestamp":int(time.time()*1000)})+'\n')
        except: pass
        # #endregion
        
        # Check if token looks like a valid Shopify token (plaintext)
        # Shopify tokens start with shpat_ or shpca_ and are ~32-40 chars
        if token.startswith('shpat_') or token.startswith('shpca_'):
            # Token is plaintext - return as-is (backwards compatibility or not encrypted)
            # #region agent log
            try:
                import json
                import time
                with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"models.py:get_access_token","message":"Returning plaintext token","data":{"token_preview":token[:10]},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
            return token
        
        # Token doesn't look like plaintext, try to decrypt
        try:
            from data_encryption import decrypt_access_token
            from logging_config import logger
            
            # #region agent log
            try:
                import json
                import time
                with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"models.py:get_access_token","message":"Attempting decryption","data":{"token_length":len(token),"token_preview":token[:20]},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
            
            # Try to decrypt
            decrypted = decrypt_access_token(token)
            
            # #region agent log
            try:
                import json
                import time
                with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"models.py:get_access_token","message":"Decryption result","data":{"decrypted_success":bool(decrypted),"decrypted_length":len(decrypted) if decrypted else 0,"decrypted_preview":decrypted[:10] if decrypted else None,"decrypted_starts_with_shpat":decrypted.startswith('shpat_') if decrypted else False},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
            
            if decrypted:
                # Verify decrypted token looks valid
                if decrypted.startswith('shpat_') or decrypted.startswith('shpca_'):
                    # #region agent log
                    try:
                        import json
                        import time
                        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"models.py:get_access_token","message":"Returning decrypted token","data":{"token_preview":decrypted[:10]},"timestamp":int(time.time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    return decrypted
                else:
                    # Decryption succeeded but result doesn't look like a token
                    logger.warning(f"Decrypted token doesn't match expected format (starts with: {decrypted[:10] if len(decrypted) > 10 else decrypted})")
                    # #region agent log
                    try:
                        import json
                        import time
                        with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                            f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"E","location":"models.py:get_access_token","message":"Decrypted token invalid format","data":{"decrypted_preview":decrypted[:20] if decrypted else None},"timestamp":int(time.time()*1000)})+'\n')
                    except: pass
                    # #endregion
                    return None
            else:
                # Decryption returned None - token might be corrupted or invalid encrypted format
                logger.warning(f"Decryption returned None for token (length: {len(token)}, starts with: {token[:20]})")
                # #region agent log
                try:
                    import json
                    import time
                    with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"models.py:get_access_token","message":"Decryption returned None","data":{"token_length":len(token),"token_preview":token[:20]},"timestamp":int(time.time()*1000)})+'\n')
                except: pass
                # #endregion
                return None
        except Exception as e:
            # If decryption fails with exception, log and return None
            from logging_config import logger
            logger.error(f"Error decrypting access token: {e}")
            # #region agent log
            try:
                import json
                import time
                with open('/Users/essentials/Documents/1EmployeeSuite-FIXED/.cursor/debug.log', 'a') as f:
                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"models.py:get_access_token","message":"Decryption exception","data":{"error":str(e)[:200]},"timestamp":int(time.time()*1000)})+'\n')
            except: pass
            # #endregion
            return None
    
    def __repr__(self):
        return f'<ShopifyStore {self.shop_url}>'
