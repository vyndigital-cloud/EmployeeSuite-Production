# 🚀 Employee Suite - Complete Application Feed
**For Claude AI - Comprehensive App Documentation**

---

## 📋 TABLE OF CONTENTS
1. [Application Overview](#application-overview)
2. [Core Features](#core-features)
3. [Architecture & Tech Stack](#architecture--tech-stack)
4. [Database Schema](#database-schema)
5. [API Endpoints](#api-endpoints)
6. [Security Implementation](#security-implementation)
7. [Shopify Integration](#shopify-integration)
8. [Billing & Subscriptions](#billing--subscriptions)
9. [Recent Fixes & Improvements](#recent-fixes--improvements)
10. [Configuration & Environment](#configuration--environment)
11. [Deployment](#deployment)
12. [File Structure](#file-structure)

---

## 🎯 APPLICATION OVERVIEW

**Employee Suite** is a Shopify app that provides comprehensive order processing, inventory management, and revenue reporting for Shopify store owners. It offers both manual operations and automated features with scheduled report delivery.

### Key Value Propositions:
- **Order Processing**: Automate order fulfillment workflows
- **Inventory Management**: Track and manage inventory levels
- **Revenue Reporting**: Comprehensive revenue analytics and reports
- **CSV Exports**: Export all reports with date filtering
- **Scheduled Reports**: Automated email/SMS delivery
- **Multi-Store Support**: Connect multiple Shopify stores
- **Data Encryption**: Secure storage of sensitive tokens

### Pricing Model:
- **7-Day Free Trial** (no credit card required)
- **$99 USD/month Premium Plan** (includes all features)

---

## ✨ CORE FEATURES

### 1. **Order Processing**
- Process pending orders
- Track paid/unfulfilled orders
- Order status management
- CSV export with date filtering

### 2. **Inventory Management**
- Real-time inventory tracking
- Low stock alerts
- Inventory level monitoring
- CSV export with date filtering

### 3. **Revenue Reporting**
- Comprehensive revenue analytics
- Financial status tracking
- Revenue trends and insights
- CSV export with date filtering

### 4. **Comprehensive Dashboard**
- Unified view of all three report types
- Real-time data aggregation
- Visual analytics
- Date range filtering

### 5. **CSV Exports**
- Export Orders, Inventory, and Revenue reports
- Date range filtering (calendar toggles)
- Auto-download settings
- Manual download option

### 6. **Scheduled Reports**
- Automated report delivery
- Email delivery
- SMS delivery option
- Customizable schedule (daily, weekly, monthly)
- Timezone support
- Custom delivery times

### 7. **User Settings**
- Auto-download preferences
- Default date range settings
- Report delivery preferences
- Email/SMS configuration

### 8. **Multi-Store Support**
- Connect multiple Shopify stores
- Store-specific data isolation
- Per-store reporting

---

## 🏗️ ARCHITECTURE & TECH STACK

### Backend:
- **Framework**: Flask (Python)
- **Database**: PostgreSQL (with SQLite fallback)
- **ORM**: SQLAlchemy (Flask-SQLAlchemy)
- **Authentication**: Flask-Login + Shopify Session Tokens
- **Session Management**: Flask-Session (server-side sessions)

### Frontend:
- **Templates**: Jinja2
- **JavaScript**: Vanilla JS + Shopify App Bridge
- **Styling**: Custom CSS (Shopify Polaris-inspired)

### External Services:
- **Shopify API**: REST + GraphQL
- **Email**: SendGrid (for scheduled reports)
- **SMS**: Twilio (for scheduled reports)
- **Error Tracking**: Sentry

### Key Libraries:
- `flask`, `flask-login`, `flask-sqlalchemy`, `flask-session`
- `requests` (HTTP client)
- `cryptography` (Fernet encryption)
- `jwt` (Shopify session token verification)
- `psycopg2-binary` (PostgreSQL driver)

---

## 🗄️ DATABASE SCHEMA

### Tables:

#### `users`
```sql
- id (PK, Integer)
- email (String, Unique, Indexed)
- password_hash (String)
- created_at (DateTime)
- trial_ends_at (DateTime) -- 7-day free trial
- is_subscribed (Boolean)
- stripe_customer_id (String, Indexed, Nullable)
- reset_token (String, Nullable)
- reset_token_expires (DateTime, Nullable)
```

#### `shopify_stores`
```sql
- id (PK, Integer)
- user_id (FK -> users.id, Indexed)
- shop_url (String, Indexed)
- shop_id (BigInteger, Indexed, Nullable)
- access_token (String, Encrypted) -- CRITICAL: Encrypted before storage
- charge_id (String, Indexed, Nullable) -- Shopify billing charge ID
- created_at (DateTime)
- is_active (Boolean, Indexed)
- uninstalled_at (DateTime, Nullable)

Indexes:
- idx_shopify_store_shop_active (shop_url, is_active) -- Composite
- idx_shopify_store_user_active (user_id, is_active) -- Composite
```

#### `user_settings`
```sql
- id (PK, Integer)
- user_id (FK -> users.id, Unique)
- auto_download_orders (Boolean)
- auto_download_inventory (Boolean)
- auto_download_revenue (Boolean)
- report_delivery_email (String, Nullable)
- report_delivery_sms (String, Nullable)
- default_date_range_days (Integer)
- created_at (DateTime)
- updated_at (DateTime)
```

#### `subscription_plans`
```sql
- id (PK, Integer)
- user_id (FK -> users.id, Indexed)
- plan_type (String) -- 'premium'
- price_usd (Numeric)
- charge_id (String, Nullable) -- Shopify charge ID
- status (String) -- 'active', 'cancelled', 'expired'
- multi_store_enabled (Boolean)
- staff_connections_enabled (Boolean)
- automated_reports_enabled (Boolean)
- scheduled_delivery_enabled (Boolean)
- created_at (DateTime)
- updated_at (DateTime)
```

#### `scheduled_reports`
```sql
- id (PK, Integer)
- user_id (FK -> users.id, Indexed)
- report_type (String) -- 'orders', 'inventory', 'revenue', 'all'
- frequency (String) -- 'daily', 'weekly', 'monthly'
- delivery_time (String) -- 'HH:MM' format
- timezone (String)
- delivery_email (String, Nullable)
- delivery_sms (String, Nullable)
- is_active (Boolean, Indexed)
- last_sent_at (DateTime, Indexed, Nullable)
- next_send_at (DateTime, Indexed, Nullable)
- created_at (DateTime)
- updated_at (DateTime)

Indexes:
- idx_scheduled_report_user_active (user_id, is_active) -- Composite
```

---

## 🔌 API ENDPOINTS

### Authentication
- `GET /login` - Login page
- `POST /login` - Login handler
- `GET /logout` - Logout handler
- `GET /auth/callback` - Shopify OAuth callback

### Dashboard
- `GET /dashboard` - Main dashboard
- `GET /api/dashboard/comprehensive` - Comprehensive dashboard data (all 3 reports)

### Reports
- `GET /api/orders` - Get orders report
- `GET /api/inventory` - Get inventory report
- `GET /api/revenue` - Get revenue report
- `GET /api/export/orders` - Export orders CSV
- `GET /api/export/inventory` - Export inventory CSV
- `GET /api/export/revenue` - Export revenue CSV

### Settings
- `GET /api/settings` - Get user settings
- `POST /api/settings` - Update user settings

### Scheduled Reports
- `GET /api/scheduled-reports` - Get all scheduled reports
- `POST /api/scheduled-reports` - Create scheduled report
- `DELETE /api/scheduled-reports/<id>` - Delete scheduled report

### Shopify Integration
- `GET /install` - Start OAuth installation
- `GET /auth/callback` - OAuth callback handler
- `GET /settings/shopify` - Shopify settings page
- `POST /settings/shopify/disconnect` - Disconnect store

### Billing
- `GET /pricing` - Pricing page
- `GET /subscribe` - Subscribe to premium plan
- `GET /billing/confirm` - Confirm subscription after Shopify approval

### Features Pages
- `GET /features/welcome` - Welcome page for new features
- `GET /features/csv-exports` - CSV exports feature page
- `GET /features/scheduled-reports` - Scheduled reports feature page
- `GET /features/dashboard` - Comprehensive dashboard page

---

## 🔒 SECURITY IMPLEMENTATION

### 1. **Access Token Encryption**
- **Location**: `data_encryption.py`
- **Method**: Fernet (symmetric encryption)
- **Key Derivation**: PBKDF2HMAC
- **Storage**: Tokens encrypted before database storage
- **Retrieval**: Automatic decryption via `ShopifyStore.get_access_token()`

### 2. **Session Management**
- **Embedded Apps**: Session tokens (Shopify App Bridge)
- **Standalone**: Flask-Login cookies
- **Session Storage**: Server-side (Flask-Session)
- **Session Refresh**: Automatic after OAuth callback

### 3. **Authentication Decorators**
- `@login_required` - Flask-Login authentication
- `@require_access` - Checks subscription/trial status
- `@verify_session_token` - Shopify session token verification (embedded apps)

### 4. **HMAC Verification**
- All Shopify OAuth requests verified with HMAC
- Prevents request tampering

### 5. **SQL Injection Prevention**
- SQLAlchemy ORM (parameterized queries)
- No raw SQL queries

### 6. **XSS Prevention**
- Jinja2 auto-escaping
- Content Security Policy headers

---

## 🛒 SHOPIFY INTEGRATION

### OAuth Flow
1. User clicks "Install" → Redirects to `/install`
2. Redirects to Shopify OAuth approval page
3. User approves → Shopify redirects to `/auth/callback`
4. Exchange code for access token
5. Store encrypted token in database
6. Redirect to dashboard

### API Scopes Required
- `read_orders`
- `read_products`
- `read_inventory`
- `write_orders` (for order processing)

### API Client
- **Class**: `ShopifyClient` (`shopify_integration.py`)
- **API Version**: 2025-10
- **Headers**: `X-Shopify-Access-Token: <raw_token>` (NOT Bearer)
- **Error Handling**: 401, 403, 429 (rate limiting)

### Token Management
- Tokens encrypted before storage
- Automatic decryption on retrieval
- Backward compatibility with plaintext tokens
- Token validation (must start with `shpat_` or `shpca_`)

---

## 💳 BILLING & SUBSCRIPTIONS

### Pricing
- **Free Trial**: 7 days (no credit card)
- **Premium Plan**: $99 USD/month

### Shopify Billing API
- **Class**: `ShopifyBilling` (`shopify_billing.py`)
- **Charge Type**: Recurring Application Charge
- **Trial Days**: 7
- **Confirmation Flow**: User approves → Redirects to `/billing/confirm`

### Subscription Management
- Charge ID stored in `shopify_stores.charge_id`
- Status checked via Shopify Billing API
- Race condition prevention (database locks)

### Access Control
- `User.has_access()` - Checks subscription OR trial
- `User.is_trial_active()` - Checks trial status
- Trial ends when user subscribes (not extended)

---

## 🔧 RECENT FIXES & IMPROVEMENTS

### Critical Fixes (January 2025)

#### 1. **Access Token Encryption**
- **Issue**: Tokens stored in plaintext
- **Fix**: Encrypt before storage, decrypt on retrieval
- **Files**: `shopify_oauth.py`, `models.py`, `data_encryption.py`

#### 2. **Session Expiration After OAuth**
- **Issue**: Users logged out after store reconnection
- **Fix**: Explicit session refresh with `session['user_id']`, `session['_authenticated']`
- **Files**: `shopify_oauth.py`, `access_control.py`

#### 3. **401 Unauthorized Errors**
- **Issue**: Token format issues after encryption
- **Fix**: Intelligent token decryption with plaintext fallback
- **Files**: `models.py`, `shopify_integration.py`

#### 4. **Billing Race Conditions**
- **Issue**: Concurrent subscription activations
- **Fix**: Database transactions with `with_for_update()` locks
- **Files**: `billing.py`, `enhanced_billing.py`, `shopify_billing.py`

#### 5. **N+1 Query Issues**
- **Issue**: Multiple queries when loading scheduled reports
- **Fix**: Eager loading with `joinedload(ScheduledReport.user)`
- **Files**: `enhanced_features.py`

#### 6. **Missing Database Indexes**
- **Issue**: Slow queries on common filters
- **Fix**: Composite indexes for `(shop_url, is_active)`, `(user_id, is_active)`
- **Files**: `models.py`, `enhanced_models.py`

#### 7. **Error Handling Gaps**
- **Issue**: Unhandled exceptions in database operations
- **Fix**: Try/except blocks for all `db.session.commit()` calls
- **Files**: `enhanced_features.py`, `enhanced_billing.py`, `shopify_billing.py`

#### 8. **Bare Exception Clauses**
- **Issue**: `except:` catching all exceptions without logging
- **Fix**: Proper exception handling with logging
- **Files**: `shopify_billing.py`

---

## ⚙️ CONFIGURATION & ENVIRONMENT

### Required Environment Variables

```bash
# Shopify App Credentials
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_SECRET=your_api_secret
SHOPIFY_APP_URL=https://your-app-url.com

# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname
# OR (fallback)
DATABASE_URL=sqlite:///employeesuite.db

# Encryption
ENCRYPTION_KEY=base64-encoded-fernet-key

# Session
SECRET_KEY=your-secret-key

# Email (for scheduled reports)
SENDGRID_API_KEY=your_sendgrid_key

# SMS (for scheduled reports)
TWILIO_ACCOUNT_SID=your_twilio_sid
TWILIO_AUTH_TOKEN=your_twilio_token
TWILIO_PHONE_NUMBER=+1234567890

# Error Tracking (optional)
SENTRY_DSN=your_sentry_dsn
```

### Generating Encryption Key
```python
from cryptography.fernet import Fernet
key = Fernet.generate_key()
print(key.decode())  # Use this as ENCRYPTION_KEY
```

---

## 🚀 DEPLOYMENT

### Platform
- **Hosting**: Render.com
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn app:app`

### Procfile
```
web: gunicorn app:app
```

### Database Migration
- Automatic on first run via `init_db()`
- Adds missing columns if needed
- Safe to run multiple times

### Health Check
- `GET /health` - Returns 200 OK

---

## 📁 FILE STRUCTURE

```
1EmployeeSuite-FIXED/
├── app.py                          # Main Flask application
├── models.py                       # Database models (User, ShopifyStore)
├── enhanced_models.py              # Additional models (UserSettings, SubscriptionPlan, ScheduledReport)
├── data_encryption.py              # Token encryption/decryption
├── shopify_integration.py          # ShopifyClient class
├── shopify_oauth.py                # OAuth flow handlers
├── shopify_billing.py              # Shopify Billing API integration
├── billing.py                      # Legacy billing (maintained for compatibility)
├── enhanced_billing.py                # Enhanced billing system
├── enhanced_features.py            # API endpoints for new features
├── features_pages.py               # Feature pages (welcome, CSV, scheduled, dashboard)
├── access_control.py               # Authentication decorators
├── session_token_verification.py   # Shopify session token verification
├── reporting.py                    # Report generation logic
├── auth.py                         # Authentication routes
├── shopify_routes.py               # Shopify-related routes
├── faq_routes.py                   # FAQ page
├── scheduled_reports_worker.py     # Background worker for scheduled reports
├── requirements.txt                # Python dependencies
├── Procfile                        # Render.com deployment config
├── .env                            # Environment variables (not in git)
└── README.md                       # Project documentation
```

---

## 🔄 KEY WORKFLOWS

### 1. User Registration & Store Connection
1. User visits app → Redirected to `/login` or OAuth
2. User logs in or installs via Shopify
3. OAuth callback creates/updates `ShopifyStore` record
4. Access token encrypted and stored
5. User redirected to dashboard

### 2. Report Generation
1. User requests report (Orders/Inventory/Revenue)
2. `ShopifyClient` fetches data from Shopify API
3. Data processed and formatted
4. Returned as JSON or CSV

### 3. Scheduled Report Delivery
1. Background worker (`scheduled_reports_worker.py`) runs periodically
2. Checks `scheduled_reports` table for due reports
3. Generates reports using `reporting.py`
4. Sends via email (SendGrid) or SMS (Twilio)
5. Updates `last_sent_at` and `next_send_at`

### 4. Subscription Flow
1. User clicks "Subscribe" → Redirected to `/subscribe`
2. Creates Shopify recurring charge
3. User approves on Shopify
4. Shopify redirects to `/billing/confirm`
5. Subscription activated with database lock
6. User access granted

---

## 🐛 KNOWN ISSUES & LIMITATIONS

### None Currently
All critical issues have been resolved in the January 2025 fixes.

### Future Enhancements
- Multi-store dashboard aggregation
- Advanced analytics and charts
- Webhook support for real-time updates
- Staff member management
- Custom report templates

---

## 📊 PERFORMANCE METRICS

### Database
- Composite indexes for common queries
- Eager loading to prevent N+1 queries
- Connection pooling (SQLAlchemy)

### API
- Request caching for inventory/products
- Rate limiting handling (429 errors)
- Automatic retry with exponential backoff

### Security
- All access tokens encrypted
- Session tokens for embedded apps
- HMAC verification for OAuth

---

## 📝 NOTES FOR CLAUDE AI

### Important Patterns
1. **Token Handling**: Always use `store.get_access_token()` instead of `store.access_token`
2. **Database Transactions**: Use `with_for_update()` for critical updates
3. **Error Handling**: Wrap all `db.session.commit()` in try/except
4. **Embedded Apps**: Check `session['_authenticated']` as backup auth
5. **API Headers**: Use `X-Shopify-Access-Token` (NOT `Authorization: Bearer`)

### Common Gotchas
- Tokens may be encrypted OR plaintext (backward compatibility)
- Embedded apps use session tokens, not cookies
- Trial ends when user subscribes (not extended)
- Database fallback to SQLite if PostgreSQL unavailable

### Testing Checklist
- [ ] OAuth flow works for new installations
- [ ] OAuth flow works for reconnections
- [ ] Session persists after OAuth callback
- [ ] Reports generate correctly
- [ ] CSV exports work with date filtering
- [ ] Scheduled reports send correctly
- [ ] Subscription activation works
- [ ] Token encryption/decryption works
- [ ] Database indexes improve query performance

---

## 📚 ADDITIONAL DOCUMENTATION

- `ERROR_SCAN_AND_FIXES.md` - Detailed error scan results
- `COMPREHENSIVE_AUDIT_REPORT.md` - Full security audit
- `TOKEN_FIX_SUMMARY.md` - Token encryption fix details
- `INTEGRATION_GUIDE.md` - Integration instructions
- `AI_AGENT_COMPREHENSIVE_GUIDE.md` - Previous comprehensive guide

---

**Last Updated**: January 2025  
**Version**: 2.0 (Post-Fix)  
**Status**: Production Ready ✅

