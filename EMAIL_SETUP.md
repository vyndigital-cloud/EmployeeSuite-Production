# Email Configuration Status

## SendGrid Setup
The application uses SendGrid for transactional emails.

### Required Environment Variable
- `SENDGRID_API_KEY` - Your SendGrid API key (starts with `SG.` and is ~69 characters long)

### How to Get a SendGrid API Key
1. Go to https://app.sendgrid.com/settings/api_keys
2. Click "Create API Key"
3. Name it "Employee Suite Production"
4. Select "Full Access" or at least "Mail Send" permission
5. Click "Create & View"
6. Copy the ENTIRE key (it's very long)

### How to Update in Render
1. Go to https://dashboard.render.com
2. Select "EmployeeSuite-Production"
3. Click "Environment" in the left sidebar
4. Find `SENDGRID_API_KEY`
5. Click "Edit" and paste your new API key
6. Click "Save Changes"
7. Render will automatically redeploy

### Verification
After updating, check the logs for:
- ✅ `SendGrid email sent to...` - Success
- ❌ `HTTP Error 401: Unauthorized` - Invalid API key
- ❌ `SENDGRID_API_KEY not set` - Missing environment variable

### Email Types Sent
- Welcome emails (new user registration)
- Password reset emails
- Trial expiration warnings
- Subscription confirmations

Last updated: 2026-02-06
