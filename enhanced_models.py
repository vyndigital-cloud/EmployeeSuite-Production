"""
Enhanced Database Models for Employee Suite
Adds: Settings, Subscription Plans, Scheduled Reports, Encryption
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from sqlalchemy.orm import validates
from models import db, User, ShopifyStore

# Subscription Plan Types
PLAN_FREE = 'free'
PLAN_PRO = 'pro'

# Plan Pricing (Updated for Production: $39/month single plan)
PLAN_PRICES = {
    PLAN_FREE: 0.00,
    PLAN_PRO: 39.00,
}

# Plan Features
PLAN_FEATURES = {
    PLAN_FREE: {
        'name': 'Free Trial',
        'price': 0,
        'stores_limit': 1,
        'data_days': 7,
        'csv_exports': False,
        'auto_download': False,
        'scheduled_reports': False,
        'email_reports': False,
        'sms_reports': False,
        'priority_support': False,
        'api_access': False,
    },
    PLAN_PRO: {
        'name': 'Employee Suite Pro',
        'price': 39,
        'stores_limit': -1,  # Unlimited
        'data_days': -1,     # Unlimited
        'csv_exports': True,
        'auto_download': True,
        'scheduled_reports': True,
        'email_reports': True,
        'sms_reports': True,
        'priority_support': True,
        'api_access': True,
    },
}

class UserSettings(db.Model):
    """User preferences and settings"""
    __tablename__ = 'user_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True, index=True)
    
    # Auto-download settings
    auto_download_orders = db.Column(db.Boolean, default=False)
    auto_download_inventory = db.Column(db.Boolean, default=False)
    auto_download_revenue = db.Column(db.Boolean, default=False)
    
    # Scheduled reports
    scheduled_reports_enabled = db.Column(db.Boolean, default=False)
    report_frequency = db.Column(db.String(20), default='daily')  # daily, weekly, monthly
    report_time = db.Column(db.String(10), default='09:00')  # HH:MM format
    report_timezone = db.Column(db.String(50), default='UTC')
    report_delivery_email = db.Column(db.String(120), nullable=True)
    report_delivery_sms = db.Column(db.String(20), nullable=True)  # Phone number
    
    # Date range preferences
    default_date_range_days = db.Column(db.Integer, default=30)  # Default to last 30 days
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='settings', uselist=False)
    
    def __repr__(self):
        return f'<UserSettings user_id={self.user_id}>'

class SubscriptionPlan(db.Model):
    """Subscription plan details"""
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    plan_type = db.Column(db.String(20), nullable=False)  # 'manual' or 'automated'
    price_usd = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Plan features (all enabled for single paid plan)
    multi_store_enabled = db.Column(db.Boolean, default=True)
    staff_connections_enabled = db.Column(db.Boolean, default=True)
    automated_reports_enabled = db.Column(db.Boolean, default=True)
    scheduled_delivery_enabled = db.Column(db.Boolean, default=True)
    
    # Shopify billing
    charge_id = db.Column(db.String(255), nullable=True, index=True)
    status = db.Column(db.String(20), default='active')  # active, cancelled, expired
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    cancelled_at = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref='subscription_plan')
    
    def __repr__(self):
        return f'<SubscriptionPlan user_id={self.user_id} plan={self.plan_type}>'

class ScheduledReport(db.Model):
    """Scheduled report delivery"""
    __tablename__ = 'scheduled_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    report_type = db.Column(db.String(20), nullable=False)  # 'orders', 'inventory', 'revenue', 'all'
    frequency = db.Column(db.String(20), default='daily')
    delivery_time = db.Column(db.String(10), default='09:00')
    timezone = db.Column(db.String(50), default='UTC')
    
    # Delivery method
    delivery_email = db.Column(db.String(120), nullable=True)
    delivery_sms = db.Column(db.String(20), nullable=True)
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)  # Added index for composite queries
    last_sent_at = db.Column(db.DateTime, nullable=True, index=True)  # Added index for queries
    next_send_at = db.Column(db.DateTime, nullable=True, index=True)  # Added index for queries
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref='scheduled_reports')
    
    # Composite index for common query pattern: filter_by(user_id=user_id, is_active=True)
    __table_args__ = (
        db.Index('idx_scheduled_report_user_active', 'user_id', 'is_active'),
    )
    
    def calculate_next_send(self):
        """Calculate next send time based on frequency"""
        now = datetime.utcnow()
        time_parts = self.delivery_time.split(':')
        hour = int(time_parts[0])
        minute = int(time_parts[1]) if len(time_parts) > 1 else 0
        
        if self.frequency == 'daily':
            next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_send <= now:
                next_send += timedelta(days=1)
        elif self.frequency == 'weekly':
            days_ahead = 7 - now.weekday()
            next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=days_ahead)
        elif self.frequency == 'monthly':
            next_send = now.replace(day=1, hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=32)
            next_send = next_send.replace(day=1)
        else:
            next_send = now + timedelta(days=1)
        
        return next_send
    
    def __repr__(self):
        return f'<ScheduledReport user_id={self.user_id} type={self.report_type}>'

# Extend User model with helper methods
def get_user_plan(user):
    """Get user's subscription plan"""
    plan = SubscriptionPlan.query.filter_by(user_id=user.id, status='active').first()
    return plan

def get_user_plan_type(user):
    """Get user's plan type string, defaults to FREE"""
    plan = get_user_plan(user)
    if plan:
        return plan.plan_type
    return PLAN_FREE

def get_plan_features(user):
    """Get features dict for user's plan"""
    plan_type = get_user_plan_type(user)
    return PLAN_FEATURES.get(plan_type, PLAN_FEATURES[PLAN_FREE])

def get_user_settings(user):
    """Get or create user settings"""
    settings = UserSettings.query.filter_by(user_id=user.id).first()
    if not settings:
        settings = UserSettings(user_id=user.id)
        db.session.add(settings)
        db.session.commit()
    return settings

def is_automated_plan(user):
    """Check if user has automated plan features (Pro plan)"""
    return user.is_subscribed

def is_pro_or_higher(user):
    """Check if user has Pro plan"""
    return user.is_subscribed

def can_export_csv(user):
    """Check if user can export CSV files - requires paid subscription"""
    return user.is_subscribed

def can_auto_download(user):
    """Check if user can use auto-download - requires paid subscription"""
    return user.is_subscribed

def can_scheduled_reports(user):
    """Check if user can use scheduled reports - requires paid subscription"""
    return user.is_subscribed

def can_multi_store(user):
    """Check if user can connect multiple stores - requires paid subscription"""
    return user.is_subscribed

def get_stores_limit(user):
    """Get max stores allowed for user's plan"""
    features = get_plan_features(user)
    return features.get('stores_limit', 1)

def get_data_days_limit(user):
    """Get max data history days for user's plan"""
    features = get_plan_features(user)
    return features.get('data_days', 7)

