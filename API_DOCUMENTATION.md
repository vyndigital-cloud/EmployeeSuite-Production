# Employee Suite API Documentation

**Version:** 1.0  
**Base URL:** `https://employeesuite-production.onrender.com`

---

## Authentication

All API endpoints (except public routes) require authentication via session cookies. Users must be logged in to access protected endpoints.

---

## Endpoints

### Dashboard

#### `GET /dashboard`
Returns the main dashboard page.

**Authentication:** Required  
**Access:** All authenticated users (expired users see subscribe prompt)

**Response:** HTML page

---

### Order Processing

#### `POST /api/process_orders`
Processes pending Shopify orders.

**Authentication:** Required  
**Access:** Subscribed users or active trial users

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "message": "Processed 5 orders successfully"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message here"
}
```

---

### Inventory Management

#### `POST /api/update_inventory`
Updates and displays inventory levels from Shopify.

**Authentication:** Required  
**Access:** Subscribed users or active trial users

**Request:**
```json
{}
```

**Response:**
```json
{
  "success": true,
  "message": "<HTML formatted inventory report>"
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Error message here"
}
```

---

### Reports

#### `POST /api/generate_report`
Generates revenue and profit reports.

**Authentication:** Required  
**Access:** Subscribed users or active trial users

**Request:**
```json
{}
```

**Response:** HTML formatted report

**Error Response:** HTML error message

---

### Health Check

#### `GET /health`
Health check endpoint for monitoring.

**Authentication:** Not required

**Response:**
```json
{
  "status": "healthy",
  "service": "Employee Suite",
  "version": "2.0",
  "database": "connected"
}
```

---

## Error Codes

- `401` - Unauthorized (not logged in)
- `403` - Forbidden (subscription expired)
- `500` - Internal server error

---

## Rate Limiting

- **Global Limit:** 200 requests per hour per IP address
- Rate limit headers are included in responses

---

## Webhooks

### Stripe Webhooks

**Endpoint:** `/webhooks/stripe`  
**Method:** POST  
**Authentication:** HMAC signature verification

### Shopify Webhooks

**Endpoints:**
- `/webhooks/app/uninstall` - App uninstallation
- `/webhooks/app_subscriptions/update` - Billing updates
- `/webhooks/customers/data_request` - GDPR data request
- `/webhooks/customers/redact` - GDPR customer deletion
- `/webhooks/shop/redact` - GDPR shop deletion

**Method:** POST  
**Authentication:** HMAC signature verification

---

## Support

For API support, contact: support@employeesuite.com

---

## Changelog

### v1.0 (2025-01-07)
- Initial API release
- Order processing endpoint
- Inventory management endpoint
- Revenue reporting endpoint
- Health check endpoint
