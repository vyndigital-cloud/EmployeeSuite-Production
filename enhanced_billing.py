"""
Enhanced Billing System for Employee Suite
Three-tier pricing: Free ($0), Pro ($29), Business ($99)

NOTE: Main pricing and subscription routes are in billing.py
This file provides the /enhanced-billing/pricing route as an alternative entry point
"""
from flask import Blueprint, redirect

enhanced_billing_bp = Blueprint('enhanced_billing', __name__)


@enhanced_billing_bp.route('/pricing', methods=['GET'])
def pricing_page():
    """Redirect to main pricing page in billing.py"""
    return redirect('/pricing')
