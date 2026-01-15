"""
Enhanced Billing System for Employee Suite
Three-tier pricing: Free ($0), Pro ($29), Business ($99)

NOTE: Main pricing and subscription routes are in billing.py
This blueprint is kept for backwards compatibility but routes are handled by billing.py
"""
from flask import Blueprint

enhanced_billing_bp = Blueprint('enhanced_billing', __name__)

# All billing routes are now handled by billing.py
# This blueprint is kept for backwards compatibility only
