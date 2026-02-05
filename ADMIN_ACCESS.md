# Admin Panel Access

## URL
**Production Admin Panel:**
```
https://employeesuite-production.onrender.com/system-admin/login
```

## Login Credentials
- **Password:** Set via `ADMIN_PASSWORD` environment variable in Render dashboard

## Important Notes
- ⚠️ Do NOT use `/admin` - this is a Render platform monitoring endpoint
- ✅ Always use `/system-admin` for the actual admin panel
- 🔒 The admin panel is password-protected and requires the ADMIN_PASSWORD

## Features
- View all users and their subscription status
- Monitor trial expirations
- Delete user accounts
- View connected Shopify stores
- System statistics dashboard

## Updating Admin Password
1. Go to Render Dashboard: https://dashboard.render.com
2. Select "EmployeeSuite-Production" service
3. Navigate to "Environment" tab
4. Find `ADMIN_PASSWORD` variable
5. Update value and save
6. Service will auto-redeploy with new password
