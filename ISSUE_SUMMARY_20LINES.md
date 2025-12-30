# Button Functionality Issue - 20 Line Summary

**Problem**: Three dashboard buttons (Process Orders, Update Inventory, Generate Report) in a Shopify embedded Flask app are frozen - visually present but clicks don't work after a recent rebuild.

**Context**: Flask app with JavaScript frontend using Shopify App Bridge. Buttons use `data-action` attributes. Authentication via session tokens (embedded) or cookies (standalone).

**Fixes Attempted**: (1) Fixed JavaScript syntax errors - missing braces and promise chain placement, (2) Added `type="button"` to prevent form submission, (3) Replaced individual event listeners with event delegation pattern, (4) Added comprehensive error logging, (5) Verified HTML structure and function availability.

**Current State**: Code deployed, syntax clean, event delegation implemented, but buttons still non-functional per user reports. Render logs show no errors - app running normally.

**Suspected Causes**: (1) Timing - functions not ready when listeners attach, (2) Event propagation blocked, (3) CSS interference (pointer-events/z-index), (4) App Bridge initialization timing, (5) Shopify iframe/CSP restrictions.

**Need Help With**: Identifying why event delegation isn't catching clicks, detecting conflicting handlers, verifying if Shopify environment blocks execution, finding any browser console errors we're missing.

**Technical Details**: Event delegation uses `document.addEventListener('click')` with capture phase, checks for `.card-btn[data-action]`, routes to `window.processOrders/updateInventory/generateReport`. Functions are defined and assigned to window object. Buttons have correct HTML structure with `type="button"` and `data-action` attributes.

**Environment**: Running on Render.com, embedded in Shopify admin iframe. App Bridge v3 for authentication. No JavaScript errors in console per user, but functionality not working.

**Debugging Status**: Comprehensive error logging added to capture all errors. Frontend logs JavaScript errors to `/api/log_error` endpoint. Backend logs all exceptions with full stack traces. Currently no errors appearing in logs, suggesting the issue may be silent failure or event not reaching handlers.

**Request**: Need external review to identify why clicks aren't reaching event handlers despite proper setup. Suspect iframe/CSP restrictions or timing issues with App Bridge initialization.
