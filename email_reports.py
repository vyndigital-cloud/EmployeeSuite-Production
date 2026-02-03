"""
Automated email reporting system for Employee Suite
"""

import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional
import os

from models import ScheduledReport, ShopifyStore, User, db
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report

logger = logging.getLogger(__name__)

def send_scheduled_reports():
    """Send all due scheduled reports"""
    try:
        now = datetime.utcnow()
        
        # Get all reports that are due
        due_reports = ScheduledReport.query.filter(
            ScheduledReport.is_active == True,
            ScheduledReport.next_send_at <= now
        ).all()
        
        logger.info(f"Found {len(due_reports)} reports to send")
        sent_count = 0
        
        for report in due_reports:
            try:
                success = send_report(report)
                if success:
                    sent_count += 1
                    
                    # Update next send time
                    report.last_sent_at = now
                    report.next_send_at = report.calculate_next_send()
                    db.session.commit()
                    
            except Exception as e:
                logger.error(f"Failed to send report {report.id}: {e}")
                db.session.rollback()
        
        return sent_count
                
    except Exception as e:
        logger.error(f"Error in send_scheduled_reports: {e}")
        return 0

def send_report(report: ScheduledReport) -> bool:
    """Send individual report"""
    try:
        user = report.user
        store = ShopifyStore.query.filter_by(user_id=user.id, is_active=True).first()
        
        if not store:
            logger.warning(f"No active store for user {user.id}, skipping report")
            return False
        
        # Generate report data based on type
        report_data = generate_report_data(store, report.report_type, user.id)
        
        if not report_data or "error" in report_data:
            logger.error(f"Failed to generate report data for {report.report_type}: {report_data}")
            return False
        
        # Send email
        return send_report_email(
            to_email=report.delivery_email,
            report_type=report.report_type,
            report_data=report_data,
            store_name=store.shop_name or store.shop_url,
            user_name=user.email
        )
        
    except Exception as e:
        logger.error(f"Error sending report {report.id}: {e}")
        return False

def generate_report_data(store: ShopifyStore, report_type: str, user_id: int) -> Dict:
    """Generate report data for email"""
    try:
        if report_type == 'orders':
            return process_orders(user_id=user_id)
        elif report_type == 'inventory':
            return update_inventory(user_id=user_id)
        elif report_type == 'revenue':
            # Get last 30 days for revenue report
            start_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
            return generate_report(user_id=user_id, start_date=start_date)
        else:
            # 'all' - get summary data
            orders_data = process_orders(user_id=user_id)
            inventory_data = update_inventory(user_id=user_id)
            revenue_data = generate_report(user_id=user_id, start_date=(datetime.utcnow() - timedelta(days=30)).isoformat())
            
            return {
                "success": True,
                "orders": orders_data.get("data", {}),
                "inventory": inventory_data.get("data", {}),
                "revenue": revenue_data.get("report_data", {})
            }
            
    except Exception as e:
        logger.error(f"Error generating report data: {e}")
        return {"error": str(e)}

def send_report_email(to_email: str, report_type: str, report_data: Dict, store_name: str, user_name: str) -> bool:
    """Send report via email"""
    try:
        # Email configuration from environment
        smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))
        smtp_username = os.getenv('SMTP_USERNAME')
        smtp_password = os.getenv('SMTP_PASSWORD')
        from_email = os.getenv('FROM_EMAIL', smtp_username)
        
        if not all([smtp_username, smtp_password]):
            logger.error("SMTP credentials not configured")
            return False
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Employee Suite <{from_email}>"
        msg['To'] = to_email
        msg['Subject'] = f"Employee Suite {report_type.title()} Report - {store_name}"
        
        # Generate HTML content
        html_content = generate_report_html(report_type, report_data, store_name, user_name)
        
        # Attach HTML content
        html_part = MIMEText(html_content, 'html')
        msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        
        logger.info(f"Report email sent to {to_email} for {report_type}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False

def generate_report_html(report_type: str, report_data: Dict, store_name: str, user_name: str) -> str:
    """Generate professional HTML email content"""
    
    current_date = datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')
    
    # Base email template
    base_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Employee Suite Report</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 0; background-color: #f8f9fa; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: white; }}
            .header {{ background: linear-gradient(135deg, #008060 0%, #00a86b 100%); color: white; padding: 30px 20px; text-align: center; }}
            .content {{ padding: 30px 20px; }}
            .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; font-size: 12px; color: #6b7280; }}
            .stat-box {{ background: #f8f9fa; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 10px 0; text-align: center; }}
            .stat-value {{ font-size: 24px; font-weight: bold; color: #008060; }}
            .stat-label {{ font-size: 14px; color: #6b7280; margin-top: 5px; }}
            .alert {{ background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; padding: 15px; margin: 15px 0; }}
            .alert-warning {{ background: #fffbeb; border-color: #fed7aa; }}
            .alert-success {{ background: #f0fdf4; border-color: #bbf7d0; }}
            .btn {{ display: inline-block; background: #008060; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: 600; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e5e7eb; }}
            th {{ background-color: #f8f9fa; font-weight: 600; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; font-size: 28px;">📊 Employee Suite Report</h1>
                <p style="margin: 10px 0 0 0; opacity: 0.9;">{report_type.title()} Report for {store_name}</p>
            </div>
            <div class="content">
                <p>Hello,</p>
                <p>Here's your automated {report_type} report generated on {current_date}.</p>
                
                {{content}}
                
                <div style="margin-top: 30px; padding: 20px; background: #f0f9ff; border-radius: 8px; border-left: 4px solid #008060;">
                    <p style="margin: 0;"><strong>💡 Need help interpreting your data?</strong></p>
                    <p style="margin: 5px 0 0 0;">Visit your Employee Suite dashboard for detailed insights and recommendations.</p>
                    <a href="https://employeesuite-production.onrender.com/dashboard" class="btn" style="margin-top: 15px;">View Dashboard</a>
                </div>
            </div>
            <div class="footer">
                <p>This automated report was generated by Employee Suite for {user_name}</p>
                <p>To modify your report settings, visit your <a href="https://employeesuite-production.onrender.com/features/scheduled-reports">dashboard</a></p>
                <p>© 2024 Employee Suite. All rights reserved.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Generate content based on report type
    if "error" in report_data:
        content = f"""
        <div class="alert">
            <h3 style="margin-top: 0; color: #dc2626;">⚠️ Report Generation Error</h3>
            <p>We encountered an error generating your {report_type} report:</p>
            <p style="font-family: monospace; background: #f3f4f6; padding: 10px; border-radius: 4px;">{report_data['error']}</p>
            <p>Our team has been notified. Please contact support if this continues.</p>
        </div>
        """
    elif report_type == 'orders':
        data = report_data.get('data', {})
        content = f"""
        <h2>📦 Orders Summary</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div class="stat-box">
                <div class="stat-value">{data.get('total_orders', 0)}</div>
                <div class="stat-label">Total Orders</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">${data.get('total_revenue', 0):,.2f}</div>
                <div class="stat-label">Total Revenue</div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div class="stat-box">
                <div class="stat-value">{data.get('pending_orders', 0)}</div>
                <div class="stat-label">Pending Orders</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">${data.get('avg_order_value', 0)}</div>
                <div class="stat-label">Avg Order Value</div>
            </div>
        </div>
        
        {f'<div class="alert alert-warning"><strong>⚠️ Action Required:</strong> You have {data.get("pending_orders", 0)} orders awaiting fulfillment.</div>' if data.get('pending_orders', 0) > 0 else '<div class="alert alert-success"><strong>✅ Great Job:</strong> All orders are fulfilled!</div>'}
        """
    elif report_type == 'inventory':
        data = report_data.get('data', {})
        content = f"""
        <h2>📦 Inventory Summary</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div class="stat-box">
                <div class="stat-value">{data.get('total_products', 0)}</div>
                <div class="stat-label">Total Products</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">${data.get('total_inventory_value', 0):,.2f}</div>
                <div class="stat-label">Inventory Value</div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div class="stat-box">
                <div class="stat-value">{data.get('low_stock_items', 0)}</div>
                <div class="stat-label">Low Stock Items</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{data.get('stock_health_score', 0)}%</div>
                <div class="stat-label">Stock Health Score</div>
            </div>
        </div>
        
        {f'<div class="alert alert-warning"><strong>⚠️ Attention Needed:</strong> {data.get("low_stock_items", 0)} items are running low on stock.</div>' if data.get('low_stock_items', 0) > 0 else '<div class="alert alert-success"><strong>✅ Excellent:</strong> Your inventory levels look healthy!</div>'}
        """
    elif report_type == 'revenue':
        data = report_data.get('report_data', {})
        content = f"""
        <h2>💰 Revenue Summary (Last 30 Days)</h2>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div class="stat-box">
                <div class="stat-value">${data.get('total_revenue', 0):,.2f}</div>
                <div class="stat-label">Total Revenue</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{data.get('total_orders', 0)}</div>
                <div class="stat-label">Total Orders</div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
            <div class="stat-box">
                <div class="stat-value">${data.get('average_order_value', 0)}</div>
                <div class="stat-label">Avg Order Value</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{'📈' if data.get('revenue_trend') == 'increasing' else '📉' if data.get('revenue_trend') == 'decreasing' else '📊'}</div>
                <div class="stat-label">Revenue Trend</div>
            </div>
        </div>
        
        <div class="alert alert-success">
            <strong>💡 Insight:</strong> {'Your revenue is trending upward - great momentum!' if data.get('revenue_trend') == 'increasing' else 'Your revenue is stable - consider marketing campaigns to boost growth.' if data.get('revenue_trend') == 'stable' else 'Revenue is declining - time to analyze and adjust your strategy.'}
        </div>
        """
    else:
        # 'all' report type
        orders_data = report_data.get('orders', {})
        inventory_data = report_data.get('inventory', {})
        revenue_data = report_data.get('revenue', {})
        
        content = f"""
        <h2>📊 Complete Store Overview</h2>
        
        <h3>📦 Orders</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
            <div class="stat-box">
                <div class="stat-value">{orders_data.get('total_orders', 0)}</div>
                <div class="stat-label">Total Orders</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{orders_data.get('pending_orders', 0)}</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">${orders_data.get('total_revenue', 0):,.2f}</div>
                <div class="stat-label">Revenue</div>
            </div>
        </div>
        
        <h3>📦 Inventory</h3>
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
            <div class="stat-box">
                <div class="stat-value">{inventory_data.get('total_products', 0)}</div>
                <div class="stat-label">Products</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{inventory_data.get('low_stock_items', 0)}</div>
                <div class="stat-label">Low Stock</div>
            </div>
            <div class="stat-box">
                <div class="stat-value">{inventory_data.get('stock_health_score', 0)}%</div>
                <div class="stat-label">Health Score</div>
            </div>
        </div>
        """
    
    return base_template.format(content=content)
