#!/bin/bash
# Update all checklists with completed items

echo "📝 Updating All Checklists..."
echo ""

# Update CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] OAuth installation route exists/- [x] OAuth installation route exists/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] OAuth callback route exists/- [x] OAuth callback route exists/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] App Bridge JavaScript loaded/- [x] App Bridge JavaScript loaded/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] App Bridge initialized/- [x] App Bridge initialized/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Session token fetching/- [x] Session token fetching/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Embedded app detection/- [x] Embedded app detection/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Database models defined/- [x] Database models defined/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Database migrations/- [x] Database migrations/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Indexes on foreign keys/- [x] Indexes on foreign keys/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Connection pooling/- [x] Connection pooling/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Shopify API version/- [x] Shopify API version/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] GraphQL API calls/- [x] GraphQL API calls/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] REST API calls/- [x] REST API calls/' CHECKLIST_01_TECHNICAL.md
sed -i.bak 's/^- \[ \] Rate limiting handled/- [x] Rate limiting handled/' CHECKLIST_01_TECHNICAL.md

# Update CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] All webhooks verify HMAC/- [x] All webhooks verify HMAC/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] HMAC uses base64/- [x] HMAC uses base64/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Raw bytes used/- [x] Raw bytes used/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Timing-safe comparison/- [x] Timing-safe comparison/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Session token verification/- [x] Session token verification/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] JWT token validation/- [x] JWT token validation/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Token signature verified/- [x] Token signature verified/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Token expiration checked/- [x] Token expiration checked/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] All user inputs validated/- [x] All user inputs validated/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] SQL injection protection/- [x] SQL injection protection/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] XSS prevention/- [x] XSS prevention/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] CSRF protection/- [x] CSRF protection/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Rate limiting configured/- [x] Rate limiting configured/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Content-Security-Policy/- [x] Content-Security-Policy/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] X-Frame-Options/- [x] X-Frame-Options/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] X-Content-Type-Options/- [x] X-Content-Type-Options/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Strict-Transport-Security/- [x] Strict-Transport-Security/' CHECKLIST_02_SECURITY.md
sed -i.bak 's/^- \[ \] Secure cookies configured/- [x] Secure cookies configured/' CHECKLIST_02_SECURITY.md

# Update CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Recurring charge creation/- [x] Recurring charge creation/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Charge activation/- [x] Charge activation/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Charge status checking/- [x] Charge status checking/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Subscription cancellation/- [x] Subscription cancellation/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Subscription page exists/- [x] Subscription page exists/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Charge creation on user/- [x] Charge creation on user/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Redirect to Shopify/- [x] Redirect to Shopify/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Callback handling/- [x] Callback handling/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Trial period handling/- [x] Trial period handling/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Subscription status tracking/- [x] Subscription status tracking/' CHECKLIST_03_BILLING.md
sed -i.bak 's/^- \[ \] Payment failure handling/- [x] Payment failure handling/' CHECKLIST_03_BILLING.md

# Update CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] customers\/data_request/- [x] customers\/data_request/' CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] customers\/redact/- [x] customers\/redact/' CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] shop\/redact/- [x] shop\/redact/' CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] All return 200 OK/- [x] All return 200 OK/' CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] app\/uninstall/- [x] app\/uninstall/' CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] app_subscriptions\/update/- [x] app_subscriptions\/update/' CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] All webhooks in app.json/- [x] All webhooks in app.json/' CHECKLIST_04_WEBHOOKS.md
sed -i.bak 's/^- \[ \] Webhooks registered/- [x] Webhooks registered/' CHECKLIST_04_WEBHOOKS.md

# Update CHECKLIST_05_LISTING.md
sed -i.bak 's/^- \[ \] App name/- [x] App name/' CHECKLIST_05_LISTING.md
sed -i.bak 's/^- \[ \] Short description/- [x] Short description/' CHECKLIST_05_LISTING.md
sed -i.bak 's/^- \[ \] Long description/- [x] Long description/' CHECKLIST_05_LISTING.md
sed -i.bak 's/^- \[ \] Privacy Policy URL/- [x] Privacy Policy URL/' CHECKLIST_05_LISTING.md
sed -i.bak 's/^- \[ \] FAQ URL/- [x] FAQ URL/' CHECKLIST_05_LISTING.md
sed -i.bak 's/^- \[ \] Support email/- [x] Support email/' CHECKLIST_05_LISTING.md

# Update CHECKLIST_08_LEGAL.md
sed -i.bak 's/^- \[ \] Privacy Policy page/- [x] Privacy Policy page/' CHECKLIST_08_LEGAL.md
sed -i.bak 's/^- \[ \] Privacy Policy content/- [x] Privacy Policy content/' CHECKLIST_08_LEGAL.md
sed -i.bak 's/^- \[ \] Terms of Service page/- [x] Terms of Service page/' CHECKLIST_08_LEGAL.md
sed -i.bak 's/^- \[ \] Terms content/- [x] Terms content/' CHECKLIST_08_LEGAL.md
sed -i.bak 's/^- \[ \] Data request endpoint/- [x] Data request endpoint/' CHECKLIST_08_LEGAL.md
sed -i.bak 's/^- \[ \] Data deletion endpoint/- [x] Data deletion endpoint/' CHECKLIST_08_LEGAL.md
sed -i.bak 's/^- \[ \] Shop deletion endpoint/- [x] Shop deletion endpoint/' CHECKLIST_08_LEGAL.md

echo "✅ All checklists updated!"
echo ""
echo "Note: Some items may need manual verification (screenshots, test accounts, etc.)"

