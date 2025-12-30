# 🚀 Employee Suite Enhanced Features - Integration Guide

## Overview

This guide explains how to integrate all the new enhanced features into your Employee Suite app.

## New Features Added

1. ✅ **CSV Downloads for All 3 Reports** with date filtering
2. ✅ **Date Range Picker/Calendar** for all reports
3. ✅ **Auto-Download Settings**
4. ✅ **Scheduled Reports** (Email/SMS delivery)
5. ✅ **Comprehensive Dashboard** showing all 3 results
6. ✅ **Data Encryption** for sensitive data
7. ✅ **Two-Tier Pricing**: $9.95 Manual, $29 Automated
8. ✅ **14-Day Free Trial**

---

## Step 1: Database Migration

Run this migration to add new tables:

```python
# Add to app.py in init_db() function or create migration script

from enhanced_models import UserSettings, SubscriptionPlan, ScheduledReport

# In init_db():
with app.app_context():
    db.create_all()  # This will create new tables
```

Or run manually:
```sql
-- User Settings Table
CREATE TABLE IF NOT EXISTS user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id),
    auto_download_orders BOOLEAN DEFAULT FALSE,
    auto_download_inventory BOOLEAN DEFAULT FALSE,
    auto_download_revenue BOOLEAN DEFAULT FALSE,
    scheduled_reports_enabled BOOLEAN DEFAULT FALSE,
    report_frequency VARCHAR(20) DEFAULT 'daily',
    report_time VARCHAR(10) DEFAULT '09:00',
    report_timezone VARCHAR(50) DEFAULT 'UTC',
    report_delivery_email VARCHAR(120),
    report_delivery_sms VARCHAR(20),
    default_date_range_days INTEGER DEFAULT 30,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Subscription Plans Table
CREATE TABLE IF NOT EXISTS subscription_plans (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    plan_type VARCHAR(20) NOT NULL,
    price_usd NUMERIC(10,2) NOT NULL,
    multi_store_enabled BOOLEAN DEFAULT FALSE,
    staff_connections_enabled BOOLEAN DEFAULT FALSE,
    automated_reports_enabled BOOLEAN DEFAULT FALSE,
    scheduled_delivery_enabled BOOLEAN DEFAULT FALSE,
    charge_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cancelled_at TIMESTAMP
);

-- Scheduled Reports Table
CREATE TABLE IF NOT EXISTS scheduled_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    report_type VARCHAR(20) NOT NULL,
    frequency VARCHAR(20) DEFAULT 'daily',
    delivery_time VARCHAR(10) DEFAULT '09:00',
    timezone VARCHAR(50) DEFAULT 'UTC',
    delivery_email VARCHAR(120),
    delivery_sms VARCHAR(20),
    is_active BOOLEAN DEFAULT TRUE,
    last_sent_at TIMESTAMP,
    next_send_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Step 2: Register Blueprints

Add to `app.py`:

```python
from enhanced_features import enhanced_bp
from enhanced_billing import enhanced_billing_bp

# Register blueprints
app.register_blueprint(enhanced_bp)
app.register_blueprint(enhanced_billing_bp)
```

---

## Step 3: Update Existing Routes

Replace existing CSV export routes with enhanced versions:

```python
# In app.py, comment out or remove:
# @app.route('/api/export/inventory', methods=['GET'])
# @app.route('/api/export/report', methods=['GET'])

# The enhanced versions are now in enhanced_bp:
# /api/export/orders (NEW!)
# /api/export/inventory (enhanced with date filtering)
# /api/export/revenue (enhanced with date filtering)
```

---

## Step 4: Environment Variables

Add to your `.env` or environment:

```bash
# Encryption key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your_encryption_key_here

# For SMS delivery (optional - use Twilio or similar)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890
```

---

## Step 5: Update User Registration

Update user registration to set 14-day trial:

```python
# In auth.py or wherever users are created:
user.trial_ends_at = datetime.utcnow() + timedelta(days=14)  # 14-day trial
```

---

## Step 6: Add Settings Page UI

Create a settings page at `/settings`:

```html
<!-- Add to templates or create new settings.html -->
<div class="settings-container">
    <h2>Settings</h2>
    
    <!-- Auto-Download Settings -->
    <section>
        <h3>Auto-Download</h3>
        <label>
            <input type="checkbox" id="auto-download-orders">
            Auto-download Orders CSV
        </label>
        <label>
            <input type="checkbox" id="auto-download-inventory">
            Auto-download Inventory CSV
        </label>
        <label>
            <input type="checkbox" id="auto-download-revenue">
            Auto-download Revenue CSV
        </label>
    </section>
    
    <!-- Scheduled Reports -->
    <section>
        <h3>Scheduled Reports</h3>
        <label>
            <input type="checkbox" id="scheduled-reports-enabled">
            Enable Scheduled Reports
        </label>
        <select id="report-frequency">
            <option value="daily">Daily</option>
            <option value="weekly">Weekly</option>
            <option value="monthly">Monthly</option>
        </select>
        <input type="time" id="report-time" value="09:00">
        <input type="email" id="report-email" placeholder="Email for reports">
        <input type="tel" id="report-sms" placeholder="SMS number (optional)">
    </section>
    
    <button onclick="saveSettings()">Save Settings</button>
</div>
```

---

## Step 7: Add Date Range Picker to Reports

Add date picker UI to dashboard:

```html
<!-- Date Range Picker -->
<div class="date-range-picker">
    <label>Date Range:</label>
    <select id="date-range-select">
        <option value="7">Last 7 days</option>
        <option value="30" selected>Last 30 days</option>
        <option value="90">Last 90 days</option>
        <option value="180">Last 6 months</option>
        <option value="365">Last year</option>
        <option value="custom">Custom range</option>
    </select>
    <input type="date" id="start-date" style="display:none;">
    <input type="date" id="end-date" style="display:none;">
</div>
```

---

## Step 8: Update Billing Routes

Update existing billing routes to use enhanced billing:

```python
# In app.py, update /subscribe route to use enhanced_billing_bp
# Or redirect to /pricing for new pricing page
```

---

## Step 9: Create Scheduled Report Worker

Create a cron job or background worker for scheduled reports:

```python
# scheduled_reports_worker.py
from enhanced_features import send_scheduled_reports
from enhanced_models import ScheduledReport
from datetime import datetime

def run_scheduled_reports():
    """Run scheduled reports - call this from cron job"""
    now = datetime.utcnow()
    
    # Find reports due to be sent
    due_reports = ScheduledReport.query.filter(
        ScheduledReport.is_active == True,
        ScheduledReport.next_send_at <= now
    ).all()
    
    for report in due_reports:
        send_scheduled_reports(report)
        report.last_sent_at = now
        report.next_send_at = report.calculate_next_send()
        db.session.commit()
```

Add to cron (every hour):
```bash
0 * * * * cd /path/to/app && python scheduled_reports_worker.py
```

---

## Step 10: Update Dashboard

Add comprehensive dashboard view:

```python
# In app.py
@app.route('/dashboard/comprehensive')
@login_required
@require_access
def comprehensive_dashboard():
    """Comprehensive dashboard showing all 3 reports"""
    return render_template('comprehensive_dashboard.html')
```

---

## Testing Checklist

- [ ] Database tables created
- [ ] Blueprints registered
- [ ] CSV exports work with date filtering
- [ ] Settings page saves correctly
- [ ] Scheduled reports create/delete works
- [ ] Two-tier pricing displays correctly
- [ ] 14-day trial works
- [ ] Encryption key set in environment
- [ ] Comprehensive dashboard loads

---

## API Endpoints Added

### CSV Exports
- `GET /api/export/orders?start_date=...&end_date=...` - Export orders CSV
- `GET /api/export/inventory?days=30` - Export inventory CSV
- `GET /api/export/revenue?start_date=...&end_date=...` - Export revenue CSV

### Settings
- `GET /api/settings` - Get user settings
- `POST /api/settings` - Update user settings

### Scheduled Reports
- `GET /api/scheduled-reports` - Get scheduled reports
- `POST /api/scheduled-reports` - Create scheduled report
- `DELETE /api/scheduled-reports/<id>` - Delete scheduled report

### Dashboard
- `GET /api/dashboard/comprehensive` - Get all 3 reports at once

### Billing
- `GET /pricing` - Pricing page
- `GET /subscribe?plan=manual|automated` - Subscribe to plan

---

## Next Steps

1. Run database migration
2. Register blueprints
3. Test all endpoints
4. Add UI components
5. Set up scheduled report worker
6. Update documentation

---

## Support

If you encounter issues:
1. Check logs: `logging_config.py`
2. Verify database tables exist
3. Check environment variables
4. Test endpoints individually

