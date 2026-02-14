"""
Frontend pages for enhanced features
- CSV exports page
- Scheduled reports page
- Comprehensive dashboard page
- Welcome/features page
"""
from flask import Blueprint, render_template, request, current_app
from flask_login import login_required, current_user
from access_control import require_access
from models import ShopifyStore, UsageEvent
from app_bridge_integration import get_app_bridge_script
from session_token_verification import stateless_auth

features_pages_bp = Blueprint('features', __name__)

# Welcome/Features Page
# Welcome/Features Page


@features_pages_bp.route('/features/welcome')
@stateless_auth
def welcome():
    """Welcome page showcasing all new features"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    # Render new template
    return render_template('features/welcome.html', shop=shop, host=host)

@features_pages_bp.route('/features/csv-exports')
@stateless_auth
@require_access
def csv_exports_page():
    """CSV exports page with date filtering"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    # Check if store is connected
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    has_store = store is not None
    
    return render_template('features/csv_exports.html', shop=shop, host=host, has_store=has_store)

@features_pages_bp.route('/features/scheduled-reports')
@stateless_auth
@require_access
def scheduled_reports_page():
    """Scheduled reports management page with full UI"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    return render_template('features/scheduled_reports.html', shop=shop, host=host)

@features_pages_bp.route('/features/dashboard')
@stateless_auth
@require_access
def comprehensive_dashboard_page():
    """Comprehensive dashboard page showing all reports"""
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    
    # Onboarding check: Has user generated any reports?
    store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
    
    show_onboarding = True
    if store:
        usage = UsageEvent.query.filter_by(store_id=store.id, event_type='report_generated').first()
        if usage:
            show_onboarding = False
            
    return render_template('features/dashboard.html', shop=shop, host=host, show_onboarding=show_onboarding)

