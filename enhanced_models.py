"""
Enhanced Models Compatibility Shim
This file re-exports classes from models.py to maintain backward compatibility
"""

# Try to import from models.py, with fallback definitions
try:
    from models import (
        PLAN_FREE, PLAN_PRO, PLAN_FEATURES,
        UserSettings, SubscriptionPlan, ScheduledReport,
        get_user_plan, get_user_plan_type, get_plan_features,
        get_user_settings, is_automated_plan, is_pro_or_higher,
        can_export_csv, can_auto_download, can_scheduled_reports,
        can_multi_store, get_stores_limit, get_data_days_limit,
        PLAN_MANUAL, PLAN_AUTOMATED
    )
    
    # Try to import PLAN_PRICES, with fallback
    try:
        from models import PLAN_PRICES
    except ImportError:
        PLAN_PRICES = {"pro": 39.00, "business": 99.00}
        
except ImportError as e:
    # Fallback definitions if models.py is missing
    import logging
    logging.getLogger(__name__).warning(f"Could not import from models: {e}. Using fallback definitions.")
    
    PLAN_FREE = "free"
    PLAN_PRO = "pro"
    PLAN_PRICES = {"pro": 39.00}
    PLAN_FEATURES = {}
    
    class UserSettings:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    class SubscriptionPlan:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
        
        @staticmethod
        def query():
            class MockQuery:
                def filter_by(self, **kwargs):
                    return self
                def first(self):
                    return None
            return MockQuery()
    
    class ScheduledReport:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    
    # Fallback functions
    def get_user_plan(user): return None
    def get_user_plan_type(user): return PLAN_FREE
    def get_plan_features(plan_type): return []
    def get_user_settings(user): return None
    def is_automated_plan(plan_type): return False
    def is_pro_or_higher(plan_type): return plan_type == PLAN_PRO
    def can_export_csv(user): return False
    def can_auto_download(user): return False
    def can_scheduled_reports(user): return False
    def can_multi_store(user): return False
    def get_stores_limit(user): return 1
    def get_data_days_limit(user): return 30
