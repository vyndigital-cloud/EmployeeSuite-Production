"""
Enhanced Features for Employee Suite
- CSV exports with date filtering
- Settings management
- Scheduled reports
- Comprehensive dashboard
"""
from flask import Blueprint, request, jsonify, Response, session
from flask_login import login_required, current_user
from functools import wraps
import csv
import io
from datetime import datetime, timedelta
from models import db, User, ShopifyStore
from enhanced_models import (
    UserSettings, SubscriptionPlan, ScheduledReport,
    get_user_settings, get_user_plan, is_automated_plan, PLAN_MANUAL, PLAN_AUTOMATED
)
from date_filtering import parse_date_range, filter_orders_by_date, get_date_range_options
from order_processing import process_orders
from inventory import check_inventory
from reporting import generate_report
from data_encryption import encrypt_access_token, decrypt_access_token
from logging_config import logger
from access_control import require_access  # Use existing require_access decorator

enhanced_bp = Blueprint('enhanced', __name__)

# ============================================================================
# CSV EXPORTS WITH DATE FILTERING
# ============================================================================

@enhanced_bp.route('/api/export/orders', methods=['GET'])
@login_required
@require_access
def export_orders_csv():
    """Export orders to CSV with date filtering"""
    try:
        from shopify_integration import ShopifyClient
        
        # Get date range
        start_date, end_date = parse_date_range()
        
        # Get user's store
        store = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first()
        if not store:
            return "No store connected", 404
        
        # Get orders - decrypt token before use
        access_token = store.get_access_token()
        if not access_token:
            return "Store not properly connected. Please reconnect your store.", 400
        client = ShopifyClient(store.shop_url, access_token)
        orders_data = client._make_request("orders.json?status=any&limit=250")
        
        if "error" in orders_data:
            return f"Error fetching orders: {orders_data['error']}", 500
        
        all_orders = orders_data.get('orders', [])
        
        # Filter by date range
        filtered_orders = filter_orders_by_date(all_orders, start_date, end_date)
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Order Name', 'Date', 'Total', 'Financial Status', 'Fulfillment Status', 'Customer Email', 'Items'])
        
        for order in filtered_orders:
            order_name = order.get('name', 'N/A')
            order_date = order.get('created_at', 'N/A')
            total = order.get('total_price', '0')
            financial_status = order.get('financial_status', 'pending')
            fulfillment_status = order.get('fulfillment_status', 'unfulfilled')
            customer_email = order.get('email', 'N/A')
            
            # Get line items
            items = []
            for item in order.get('line_items', []):
                items.append(f"{item.get('title', 'N/A')} x{item.get('quantity', 1)}")
            items_str = '; '.join(items) if items else 'N/A'
            
            writer.writerow([
                order_name,
                order_date,
                total,
                financial_status,
                fulfillment_status,
                customer_email,
                items_str
            ])
        
        # Check auto-download setting
        settings = get_user_settings(current_user)
        auto_download = settings.auto_download_orders if settings else False
        
        # Return CSV file
        filename = f"orders_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        return response
        
    except Exception as e:
        logger.error(f"Error in export_orders_csv: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An error occurred exporting orders",
            "error_id": datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        }), 500

@enhanced_bp.route('/api/export/inventory', methods=['GET'])
@login_required
@require_access
def export_inventory_csv_enhanced():
    """Export inventory to CSV with date filtering support"""
    try:
        from date_filtering import parse_date_range
        
        # Get date range (for future use - inventory doesn't typically have dates)
        start_date, end_date = parse_date_range()
        
        # Get inventory data
        result = check_inventory()
        if not result.get('success'):
            return result.get('error', 'Error fetching inventory'), 500
        
        inventory_data = session.get('inventory_data', [])
        if not inventory_data:
            # Try to extract from result
            if 'inventory_data' in result:
                inventory_data = result['inventory_data']
                session['inventory_data'] = inventory_data
        
        if not inventory_data:
            return "No inventory data available", 404
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'SKU', 'Stock', 'Price', 'Variant', 'Updated'])
        
        for item in inventory_data:
            writer.writerow([
                item.get('product', 'N/A'),
                item.get('sku', 'N/A'),
                item.get('stock', 0),
                item.get('price', 'N/A'),
                item.get('variant', 'N/A'),
                datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
            ])
        
        # Check auto-download setting
        settings = get_user_settings(current_user)
        auto_download = settings.auto_download_inventory if settings else False
        
        filename = f"inventory_{datetime.utcnow().strftime('%Y%m%d')}.csv"
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        return response
        
    except Exception as e:
        logger.error(f"Error in export_inventory_csv_enhanced: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An error occurred exporting inventory",
            "error_id": datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        }), 500

@enhanced_bp.route('/api/export/revenue', methods=['GET'])
@login_required
@require_access
def export_revenue_csv_enhanced():
    """Export revenue report to CSV with date filtering"""
    try:
        from date_filtering import parse_date_range
        
        # Get date range
        start_date, end_date = parse_date_range()
        
        # Get report data
        result = generate_report()
        if not result.get('success'):
            return result.get('error', 'Error generating report'), 500
        
        report_data = session.get('report_data', {})
        if not report_data and 'report_data' in result:
            report_data = result['report_data']
            session['report_data'] = report_data
        
        if not report_data or 'products' not in report_data:
            return "No report data available", 404
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['Product', 'Revenue', 'Percentage', 'Total Revenue', 'Total Orders', 'Date Range'])
        
        total_revenue = report_data.get('total_revenue', 0)
        total_orders = report_data.get('total_orders', 0)
        date_range_str = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        
        for product, revenue in report_data.get('products', []):
            percentage = (revenue / total_revenue * 100) if total_revenue > 0 else 0
            writer.writerow([
                product,
                f"${revenue:,.2f}",
                f"{percentage:.1f}%",
                f"${total_revenue:,.2f}",
                total_orders,
                date_range_str
            ])
        
        # Check auto-download setting
        settings = get_user_settings(current_user)
        auto_download = settings.auto_download_revenue if settings else False
        
        filename = f"revenue_{start_date.strftime('%Y%m%d')}_to_{end_date.strftime('%Y%m%d')}.csv"
        response = Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment; filename={filename}'}
        )
        return response
        
    except Exception as e:
        logger.error(f"Error in export_revenue_csv_enhanced: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "An error occurred exporting revenue",
            "error_id": datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        }), 500

# ============================================================================
# SETTINGS MANAGEMENT
# ============================================================================

@enhanced_bp.route('/api/settings', methods=['GET'])
@login_required
@require_access
def get_settings():
    """Get user settings"""
    try:
        settings = get_user_settings(current_user)
        return jsonify({
            'auto_download_orders': settings.auto_download_orders,
            'auto_download_inventory': settings.auto_download_inventory,
            'auto_download_revenue': settings.auto_download_revenue,
            'scheduled_reports_enabled': settings.scheduled_reports_enabled,
            'report_frequency': settings.report_frequency,
            'report_time': settings.report_time,
            'report_timezone': settings.report_timezone,
            'report_delivery_email': settings.report_delivery_email,
            'report_delivery_sms': settings.report_delivery_sms,
            'default_date_range_days': settings.default_date_range_days
        })
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@enhanced_bp.route('/api/settings', methods=['POST'])
@login_required
@require_access
def update_settings():
    """Update user settings"""
    try:
        settings = get_user_settings(current_user)
        data = request.get_json()
        
        # Update settings
        if 'auto_download_orders' in data:
            settings.auto_download_orders = bool(data['auto_download_orders'])
        if 'auto_download_inventory' in data:
            settings.auto_download_inventory = bool(data['auto_download_inventory'])
        if 'auto_download_revenue' in data:
            settings.auto_download_revenue = bool(data['auto_download_revenue'])
        if 'scheduled_reports_enabled' in data:
            settings.scheduled_reports_enabled = bool(data['scheduled_reports_enabled'])
        if 'report_frequency' in data:
            settings.report_frequency = data['report_frequency']
        if 'report_time' in data:
            settings.report_time = data['report_time']
        if 'report_timezone' in data:
            settings.report_timezone = data['report_timezone']
        if 'report_delivery_email' in data:
            settings.report_delivery_email = data['report_delivery_email']
        if 'report_delivery_sms' in data:
            settings.report_delivery_sms = data['report_delivery_sms']
        if 'default_date_range_days' in data:
            settings.default_date_range_days = int(data['default_date_range_days'])
        
        settings.updated_at = datetime.utcnow()
        try:
            db.session.commit()
        except Exception as commit_error:
            logger.error(f"Error committing settings update: {commit_error}", exc_info=True)
            db.session.rollback()
            return jsonify({"error": "Failed to save settings"}), 500
        
        return jsonify({"success": True, "message": "Settings updated"})
    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500

# ============================================================================
# SCHEDULED REPORTS
# ============================================================================

@enhanced_bp.route('/api/scheduled-reports', methods=['GET'])
@login_required
@require_access
def get_scheduled_reports():
    """Get user's scheduled reports"""
    try:
        # Use eager loading to prevent N+1 queries if accessing report.user later
        from sqlalchemy.orm import joinedload
        reports = ScheduledReport.query.options(joinedload(ScheduledReport.user)).filter_by(user_id=current_user.id, is_active=True).all()
        return jsonify({
            'reports': [{
                'id': r.id,
                'report_type': r.report_type,
                'frequency': r.frequency,
                'delivery_time': r.delivery_time,
                'timezone': r.timezone,
                'delivery_email': r.delivery_email,
                'delivery_sms': r.delivery_sms,
                'last_sent_at': r.last_sent_at.isoformat() if r.last_sent_at else None,
                'next_send_at': r.next_send_at.isoformat() if r.next_send_at else None
            } for r in reports]
        })
    except Exception as e:
        logger.error(f"Error getting scheduled reports: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@enhanced_bp.route('/api/scheduled-reports', methods=['POST'])
@login_required
@require_access
def create_scheduled_report():
    """Create a scheduled report"""
    try:
        data = request.get_json()
        
        # Check if user has automated plan
        if not is_automated_plan(current_user):
            return jsonify({"error": "Automated plan required for scheduled reports"}), 403
        
        report = ScheduledReport(
            user_id=current_user.id,
            report_type=data.get('report_type', 'all'),
            frequency=data.get('frequency', 'daily'),
            delivery_time=data.get('delivery_time', '09:00'),
            timezone=data.get('timezone', 'UTC'),
            delivery_email=data.get('delivery_email'),
            delivery_sms=data.get('delivery_sms')
        )
        
        report.next_send_at = report.calculate_next_send()
        db.session.add(report)
        try:
            db.session.commit()
        except Exception as commit_error:
            logger.error(f"Error committing scheduled report: {commit_error}", exc_info=True)
            db.session.rollback()
            return jsonify({"error": "Failed to create scheduled report"}), 500
        
        return jsonify({"success": True, "report_id": report.id})
    except Exception as e:
        logger.error(f"Error creating scheduled report: {str(e)}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500

@enhanced_bp.route('/api/scheduled-reports/<int:report_id>', methods=['DELETE'])
@login_required
@require_access
def delete_scheduled_report(report_id):
    """Delete a scheduled report"""
    try:
        report = ScheduledReport.query.filter_by(id=report_id, user_id=current_user.id).first()
        if not report:
            return jsonify({"error": "Report not found"}), 404
        
        report.is_active = False
        try:
            db.session.commit()
        except Exception as commit_error:
            logger.error(f"Error committing scheduled report deletion: {commit_error}", exc_info=True)
            db.session.rollback()
            return jsonify({"error": "Failed to delete scheduled report"}), 500
        
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Error deleting scheduled report: {str(e)}", exc_info=True)
        try:
            db.session.rollback()
        except Exception:
            pass
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# ============================================================================
# SCHEDULED REPORT SENDING
# ============================================================================

def send_scheduled_report(report):
    """Send a scheduled report via email or SMS"""
    try:
        from email_service import send_email
        from shopify_integration import ShopifyClient
        from models import ShopifyStore
        
        # Get user's store
        store = ShopifyStore.query.filter_by(user_id=report.user_id, is_active=True).first()
        if not store:
            logger.warning(f"No active store for user {report.user_id}")
            return False
        
        # Generate reports based on type
        reports_data = {}
        
        if report.report_type in ['orders', 'all']:
            orders_result = process_orders(user_id=report.user_id)
            reports_data['orders'] = orders_result
        
        if report.report_type in ['inventory', 'all']:
            inventory_result = check_inventory(user_id=report.user_id)
            reports_data['inventory'] = inventory_result
        
        if report.report_type in ['revenue', 'all']:
            revenue_result = generate_report(user_id=report.user_id)
            reports_data['revenue'] = revenue_result
        
        # Build email content
        email_body = f"""
        <h2>Employee Suite Scheduled Report</h2>
        <p>Your scheduled {report.report_type} report is ready.</p>
        <p>Frequency: {report.frequency}</p>
        <p>Generated at: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>
        """
        
        # Add report data
        for report_name, report_result in reports_data.items():
            if report_result.get('success'):
                email_body += f"<h3>{report_name.title()} Report</h3>"
                email_body += report_result.get('message', 'No data available')
            else:
                email_body += f"<p>Error generating {report_name} report: {report_result.get('error', 'Unknown error')}</p>"
        
        # Send email if configured
        if report.delivery_email:
            try:
                from email_service import send_email
                # Create email using SendGrid
                from sendgrid import SendGridAPIClient
                from sendgrid.helpers.mail import Mail
                import os
                
                message = Mail(
                    from_email=('adam@golproductions.com', 'Employee Suite'),
                    to_emails=report.delivery_email,
                    subject=f"Employee Suite {report.report_type.title()} Report - {datetime.utcnow().strftime('%Y-%m-%d')}",
                    html_content=email_body
                )
                
                sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
                sg.send(message)
                logger.info(f"Sent scheduled report {report.id} to email {report.delivery_email}")
            except Exception as e:
                logger.error(f"Error sending email for report {report.id}: {str(e)}")
        
        # Send SMS if configured (requires Twilio setup)
        if report.delivery_sms:
            try:
                sms_sent = send_sms_notification(report.delivery_sms, f"Employee Suite Report: Your {report.report_type} report is ready.")
                if sms_sent:
                    logger.info(f"Sent SMS for report {report.id} to {report.delivery_sms}")
                else:
                    logger.warning(f"SMS delivery failed for report {report.id} - Twilio not configured")
            except Exception as e:
                logger.error(f"Error sending SMS for report {report.id}: {str(e)}")
        
        return True
    except Exception as e:
        logger.error(f"Error sending scheduled report {report.id}: {str(e)}", exc_info=True)
        return False


def send_sms_notification(phone_number, message):
    """Send SMS via Twilio (requires TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN)"""
    try:
        import os
        # Check if Twilio is available
        try:
            from twilio.rest import Client
        except ImportError:
            logger.warning("Twilio not installed - SMS notifications disabled")
            return False
        
        account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        from_number = os.getenv('TWILIO_PHONE_NUMBER')
        
        if not all([account_sid, auth_token, from_number]):
            logger.warning("Twilio credentials not configured - SMS disabled")
            return False
            
        client = Client(account_sid, auth_token)
        client.messages.create(
            body=message,
            from_=from_number,
            to=phone_number
        )
        return True
    except Exception as e:
        logger.error(f"SMS send failed: {e}")
        return False

# ============================================================================
# COMPREHENSIVE DASHBOARD
# ============================================================================

@enhanced_bp.route('/api/dashboard/comprehensive', methods=['GET'])
@login_required
@require_access
def get_comprehensive_dashboard():
    """Get comprehensive dashboard with all 3 reports"""
    try:
        # Get date range
        start_date, end_date = parse_date_range()
        
        # Get all three reports with error handling
        results = {
            'orders': None,
            'inventory': None,
            'revenue': None,
            'errors': []
        }
        
        # Try to get orders
        try:
            orders_result = process_orders()
            results['orders'] = orders_result
        except Exception as e:
            error_msg = str(e)
            if '403' in error_msg or 'Permission denied' in error_msg or 'missing required scopes' in error_msg:
                results['errors'].append({
                    'type': 'orders',
                    'error': 'Missing API permissions. Please reconnect your store at Settings → Shopify to grant required permissions.',
                    'action': 'reconnect_store'
                })
            else:
                results['errors'].append({
                    'type': 'orders',
                    'error': f'Error loading orders: {error_msg}'
                })
            logger.warning(f"Error getting orders for comprehensive dashboard: {e}")
        
        # Try to get inventory
        try:
            inventory_result = check_inventory()
            results['inventory'] = inventory_result
        except Exception as e:
            error_msg = str(e)
            if '403' in error_msg or 'Permission denied' in error_msg:
                results['errors'].append({
                    'type': 'inventory',
                    'error': 'Missing API permissions. Please reconnect your store at Settings → Shopify.',
                    'action': 'reconnect_store'
                })
            else:
                results['errors'].append({
                    'type': 'inventory',
                    'error': f'Error loading inventory: {error_msg}'
                })
            logger.warning(f"Error getting inventory for comprehensive dashboard: {e}")
        
        # Try to get revenue
        try:
            revenue_result = generate_report()
            results['revenue'] = revenue_result
        except Exception as e:
            error_msg = str(e)
            if '403' in error_msg or 'Permission denied' in error_msg or 'missing required scopes' in error_msg:
                results['errors'].append({
                    'type': 'revenue',
                    'error': 'Missing API permissions. Please reconnect your store at Settings → Shopify to grant required permissions.',
                    'action': 'reconnect_store'
                })
            else:
                results['errors'].append({
                    'type': 'revenue',
                    'error': f'Error loading revenue: {error_msg}'
                })
            logger.warning(f"Error getting revenue for comprehensive dashboard: {e}")
        
        return jsonify({
            'success': len(results['errors']) == 0 or any([results['orders'], results['inventory'], results['revenue']]),
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'orders': results['orders'],
            'inventory': results['inventory'],
            'revenue': results['revenue'],
            'errors': results['errors'],
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting comprehensive dashboard: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Failed to load dashboard: {str(e)}',
            'message': 'Please try again or reconnect your store at Settings → Shopify if you see permission errors.'
        }), 500

