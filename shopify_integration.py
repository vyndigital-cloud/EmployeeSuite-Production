import logging
import os
import time

import requests

from config import SHOPIFY_API_VERSION
from performance import CACHE_TTL_INVENTORY, CACHE_TTL_ORDERS, cache_result
from error_logging import error_logger, log_errors

logger = logging.getLogger(__name__)


class ShopifyClient:
    def __init__(self, shop_url, access_token):
        self.shop_url = shop_url.replace("https://", "").replace("http://", "")
        
        # Handle encrypted tokens with proper error handling
        if access_token and not (
            access_token.startswith("shpat_") or access_token.startswith("shpca_")
        ):
            try:
                from data_encryption import decrypt_access_token
                decrypted = decrypt_access_token(access_token)
                if decrypted:
                    self.access_token = decrypted
                    logger.info(f"Successfully decrypted token for {shop_url}")
                else:
                    logger.warning(f"Token decryption failed for {shop_url}")
                    self.access_token = None
            except ImportError:
                logger.warning("data_encryption module not available, using token as-is")
                self.access_token = access_token
            except Exception as e:
                logger.error(f"Token handling failed for {shop_url}: {e}")
                self.access_token = None
        else:
            self.access_token = access_token
        
        self.api_version = SHOPIFY_API_VERSION
        
        # Validate token
        if not self.access_token:
            logger.error(f"No valid access token for {shop_url}")
        elif not (self.access_token.startswith("shpat_") or self.access_token.startswith("shpca_")):
            logger.warning(f"Access token format may be invalid for {shop_url}")

    def _get_headers(self):
        # Debug logging: Verify token format before API call
        if self.access_token:
            token_preview = (
                self.access_token[:10]
                if len(self.access_token) > 10
                else self.access_token
            )
            token_length = len(self.access_token)
            logger.debug(
                f"Using token for API call: {token_preview}... (length: {token_length})"
            )
        else:
            logger.error("CRITICAL: No access token available for API call!")

        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json",
        }

    @log_errors("SHOPIFY_API_ERROR")
    def _make_request(self, endpoint, retries=3):
        """Make API request with comprehensive error logging"""
        url = f"https://{self.shop_url}/admin/api/{self.api_version}/{endpoint}"
        headers = self._get_headers()
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        headers["Pragma"] = "no-cache"
        headers["Expires"] = "0"
        start_time = time.time()

        for attempt in range(retries):
            try:
                response = requests.get(
                    url, headers=headers, timeout=10
                )  # Reduced for faster failures
                response_time = (time.time() - start_time) * 1000
                
                # Log API call
                error_logger.log_api_call(
                    endpoint, "GET", response.status_code, response_time
                )
                
                # CRITICAL: Check status code BEFORE raise_for_status to handle 403 properly
                status_code = response.status_code
                if status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    error_logger.log_error(
                        Exception(error_detail), 
                        "SHOPIFY_PERMISSION_ERROR",
                        {'endpoint': endpoint, 'shop_url': self.shop_url}
                    )
                    response_text = ""
                    try:
                        response_text = response.text[:500]
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            errors = error_data.get("errors", {})
                            if isinstance(errors, dict):
                                # Try multiple error fields
                                error_detail = errors.get(
                                    "base",
                                    errors.get(
                                        "message", errors.get("error", [error_detail])
                                    ),
                                )
                                if isinstance(error_detail, list):
                                    error_detail = (
                                        error_detail[0]
                                        if error_detail
                                        else "Access denied - Missing required permissions"
                                    )
                                elif not error_detail:
                                    error_detail = (
                                        "Access denied - Missing required permissions"
                                    )
                            elif isinstance(errors, str):
                                error_detail = errors
                            elif isinstance(errors, list) and errors:
                                error_detail = (
                                    errors[0]
                                    if isinstance(errors[0], str)
                                    else str(errors[0])
                                )
                            # Also check top-level error fields
                            if (
                                error_detail
                                == "Access denied - Missing required permissions"
                            ):
                                error_detail = error_data.get(
                                    "message", error_data.get("error", error_detail)
                                )
                        elif isinstance(error_data, str):
                            error_detail = error_data
                    except (ValueError, AttributeError, TypeError) as parse_error:
                        # Use response text if JSON parsing failed
                        if response_text:
                            error_detail = (
                                response_text[:200]
                                if len(response_text) < 200
                                else response_text[:200] + "..."
                            )
                    return {
                        "error": f"{error_detail} - Check your app permissions",
                        "permission_denied": True,
                    }
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                error_logger.log_error(
                    Exception("Request timeout"), 
                    "SHOPIFY_TIMEOUT_ERROR",
                    {'endpoint': endpoint, 'attempt': attempt + 1, 'shop_url': self.shop_url}
                )
                return {
                    "error": "Request timeout - Shopify API is taking too long to respond"
                }
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                error_logger.log_error(
                    Exception("Connection error"), 
                    "SHOPIFY_CONNECTION_ERROR",
                    {'endpoint': endpoint, 'attempt': attempt + 1, 'shop_url': self.shop_url}
                )
                return {
                    "error": "Connection error - Cannot connect to Shopify. Check your internet connection."
                }
            except requests.exceptions.HTTPError as e:
                # CRITICAL: Handle HTTP errors with proper error extraction
                status_code = (
                    e.response.status_code
                    if hasattr(e, "response") and e.response
                    else None
                )

                error_logger.log_error(
                    e, 
                    "SHOPIFY_HTTP_ERROR",
                    {
                        'endpoint': endpoint,
                        'status_code': status_code,
                        'shop_url': self.shop_url,
                        'response_time': (time.time() - start_time) * 1000
                    }
                )

                # Don't retry on HTTP errors (4xx, 5xx) - these are permanent
                if status_code == 401:
                    # Authentication failed - token may be expired or revoked
                    error_detail = "Authentication failed"
                    try:
                        if hasattr(e, "response") and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = error_data.get("errors", {}).get(
                                    "base", [error_detail]
                                )
                                if isinstance(error_detail, list):
                                    error_detail = (
                                        error_detail[0]
                                        if error_detail
                                        else "Authentication failed"
                                    )
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {
                        "error": f"{error_detail} - Please reconnect your store",
                        "auth_failed": True,
                    }
                elif status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    response_text = ""
                    try:
                        if hasattr(e, 'response') and e.response:
                            response_text = e.response.text[:500]
                            error_data = e.response.json()
                        else:
                            error_data = {}
                        if isinstance(error_data, dict):
                            errors = error_data.get("errors", {})
                            if isinstance(errors, dict):
                                # Try multiple error fields
                                error_detail = errors.get(
                                    "base",
                                    errors.get(
                                        "message", errors.get("error", [error_detail])
                                    ),
                                )
                                if isinstance(error_detail, list):
                                    error_detail = (
                                        error_detail[0]
                                        if error_detail
                                        else "Access denied - Missing required permissions"
                                    )
                                elif not error_detail:
                                    error_detail = (
                                        "Access denied - Missing required permissions"
                                    )
                            elif isinstance(errors, str):
                                error_detail = errors
                            elif isinstance(errors, list) and errors:
                                error_detail = (
                                    errors[0]
                                    if isinstance(errors[0], str)
                                    else str(errors[0])
                                )
                            # Also check top-level error fields
                            if (
                                error_detail
                                == "Access denied - Missing required permissions"
                            ):
                                error_detail = error_data.get(
                                    "message", error_data.get("error", error_detail)
                                )
                        elif isinstance(error_data, str):
                            error_detail = error_data
                    except (ValueError, AttributeError, TypeError) as parse_error:
                        # Use response text if JSON parsing failed
                        if response_text:
                            error_detail = (
                                response_text[:200]
                                if len(response_text) < 200
                                else response_text[:200] + "..."
                            )
                    return {
                        "error": f"{error_detail} - Check your app permissions",
                        "permission_denied": True,
                    }
                elif status_code == 429:
                    # Rate limit - wait but not too long
                    if attempt < retries - 1:
                        import time

                        time.sleep(min(2, 1 * (attempt + 1)))  # Max 2 seconds
                        continue
                    return {
                        "error": "Rate limit exceeded - Please wait a moment and try again"
                    }
                elif status_code:
                    error_detail = f"API error: {status_code}"
                    try:
                        if hasattr(e, "response") and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = str(
                                    error_data.get("errors", error_detail)
                                )
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": error_detail}
                return {"error": f"API error: {status_code or 'Unknown'}"}
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time

                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                error_logger.log_error(
                    e, 
                    "SHOPIFY_REQUEST_ERROR",
                    {
                        'endpoint': endpoint,
                        'attempt': attempt + 1,
                        'shop_url': self.shop_url,
                        'response_time': (time.time() - start_time) * 1000
                    }
                )
                return {"error": f"Request failed: {str(e)}"}

        return {"error": "Request failed after multiple attempts"}

    def _make_graphql_request(self, query, variables=None, retries=3):
        """
        Make GraphQL request with automatic retry logic (professional standard)
        Retries on network errors with exponential backoff
        """
        url = f"https://{self.shop_url}/admin/api/{self.api_version}/graphql.json"
        headers = self._get_headers()
        headers["Cache-Control"] = "no-cache, no-store, must-revalidate"

        payload = {"query": query}
        if variables:
            payload["variables"] = variables

        for attempt in range(retries):
            try:
                response = requests.post(
                    url, json=payload, headers=headers, timeout=10
                )  # Reduced from 15s for faster failures
                # CRITICAL: Check status code BEFORE raise_for_status to handle 403 properly
                status_code = response.status_code
                if status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    response_text = ""
                    try:
                        response_text = response.text[:500]
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            errors = error_data.get("errors", {})
                            if isinstance(errors, dict):
                                # Try multiple error fields
                                error_detail = errors.get(
                                    "base",
                                    errors.get(
                                        "message", errors.get("error", [error_detail])
                                    ),
                                )
                                if isinstance(error_detail, list):
                                    error_detail = (
                                        error_detail[0]
                                        if error_detail
                                        else "Access denied - Missing required permissions"
                                    )
                                elif not error_detail:
                                    error_detail = (
                                        "Access denied - Missing required permissions"
                                    )
                            elif isinstance(errors, str):
                                error_detail = errors
                            elif isinstance(errors, list) and errors:
                                error_detail = (
                                    errors[0]
                                    if isinstance(errors[0], str)
                                    else str(errors[0])
                                )
                            # Also check top-level error fields
                            if (
                                error_detail
                                == "Access denied - Missing required permissions"
                            ):
                                error_detail = error_data.get(
                                    "message", error_data.get("error", error_detail)
                                )
                        elif isinstance(error_data, str):
                            error_detail = error_data
                    except (ValueError, AttributeError, TypeError) as parse_error:
                        # Use response text if JSON parsing failed
                        if response_text:
                            error_detail = (
                                response_text[:200]
                                if len(response_text) < 200
                                else response_text[:200] + "..."
                            )
                    return {
                        "error": f"{error_detail} - Check your app permissions",
                        "permission_denied": True,
                    }
                response.raise_for_status()

                # CRITICAL: Parse JSON response and check for GraphQL errors
                # GraphQL can return 200 status even when there are errors in the response
                try:
                    response_json = response.json()
                    logger.info(
                        f"GraphQL response received: {list(response_json.keys())}"
                    )

                    # Check for GraphQL errors in the response
                    if "errors" in response_json:
                        errors = response_json["errors"]
                        logger.error(f"GraphQL errors in response: {errors}")
                        # Extract error message(s)
                        if isinstance(errors, list) and len(errors) > 0:
                            error_msg = (
                                errors[0].get("message", str(errors[0]))
                                if isinstance(errors[0], dict)
                                else str(errors[0])
                            )
                        else:
                            error_msg = str(errors)
                        return {
                            "error": f"GraphQL error: {error_msg}",
                            "graphql_errors": errors,
                        }

                    # Check if data is present
                    if "data" not in response_json:
                        logger.warning(
                            f"GraphQL response missing 'data' field: {response_json}"
                        )
                        return {
                            "error": "GraphQL response missing data field",
                            "response": response_json,
                        }

                    # Log successful response structure for debugging
                    logger.debug(
                        f"GraphQL response structure: data keys = {list(response_json.get('data', {}).keys())}"
                    )

                    return response_json
                except ValueError as json_error:
                    # Failed to parse JSON
                    logger.error(
                        f"Failed to parse GraphQL response as JSON: {json_error}"
                    )
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(
                        f"Response text (first 500 chars): {response.text[:500]}"
                    )
                    return {
                        "error": f"Failed to parse GraphQL response: {str(json_error)}"
                    }
                except Exception as parse_error:
                    # Any other parsing error
                    logger.error(
                        f"Unexpected error parsing GraphQL response: {parse_error}"
                    )
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(
                        f"Response text (first 500 chars): {response.text[:500]}"
                    )
                    return {
                        "error": f"Error parsing GraphQL response: {str(parse_error)}"
                    }
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time

                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                return {
                    "error": "Request timeout - Shopify API is taking too long to respond"
                }
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time

                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                return {
                    "error": "Connection error - Cannot connect to Shopify. Check your internet connection."
                }
            except requests.exceptions.HTTPError as e:
                # CRITICAL: Handle HTTP errors with proper error extraction
                status_code = (
                    e.response.status_code
                    if hasattr(e, "response") and e.response
                    else None
                )

                # Don't retry on HTTP errors (4xx, 5xx) - these are permanent
                if status_code == 401:
                    # Authentication failed - token may be expired or revoked
                    error_detail = "Authentication failed"
                    try:
                        if hasattr(e, "response") and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = error_data.get("errors", {}).get(
                                    "base", [error_detail]
                                )
                                if isinstance(error_detail, list):
                                    error_detail = (
                                        error_detail[0]
                                        if error_detail
                                        else "Authentication failed"
                                    )
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {
                        "error": f"{error_detail} - Please reconnect your store",
                        "auth_failed": True,
                    }
                elif status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    response_text = ""
                    try:
                        if hasattr(e, 'response') and e.response:
                            response_text = e.response.text[:500]
                            error_data = e.response.json()
                        else:
                            error_data = {}
                        if isinstance(error_data, dict):
                            errors = error_data.get("errors", {})
                            if isinstance(errors, dict):
                                # Try multiple error fields
                                error_detail = errors.get(
                                    "base",
                                    errors.get(
                                        "message", errors.get("error", [error_detail])
                                    ),
                                )
                                if isinstance(error_detail, list):
                                    error_detail = (
                                        error_detail[0]
                                        if error_detail
                                        else "Access denied - Missing required permissions"
                                    )
                                elif not error_detail:
                                    error_detail = (
                                        "Access denied - Missing required permissions"
                                    )
                            elif isinstance(errors, str):
                                error_detail = errors
                            elif isinstance(errors, list) and errors:
                                error_detail = (
                                    errors[0]
                                    if isinstance(errors[0], str)
                                    else str(errors[0])
                                )
                            # Also check top-level error fields
                            if (
                                error_detail
                                == "Access denied - Missing required permissions"
                            ):
                                error_detail = error_data.get(
                                    "message", error_data.get("error", error_detail)
                                )
                        elif isinstance(error_data, str):
                            error_detail = error_data
                    except (ValueError, AttributeError, TypeError) as parse_error:
                        # Use response text if JSON parsing failed
                        if response_text:
                            error_detail = (
                                response_text[:200]
                                if len(response_text) < 200
                                else response_text[:200] + "..."
                            )
                    return {
                        "error": f"{error_detail} - Check your app permissions",
                        "permission_denied": True,
                    }
                elif status_code == 429:
                    # Rate limit - wait but not too long
                    if attempt < retries - 1:
                        import time

                        time.sleep(min(2, 1 * (attempt + 1)))  # Max 2 seconds
                        continue
                    return {
                        "error": "Rate limit exceeded - Please wait a moment and try again"
                    }
                elif status_code:
                    error_detail = f"API error: {status_code}"
                    try:
                        if hasattr(e, "response") and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = str(
                                    error_data.get("errors", error_detail)
                                )
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": error_detail}
                return {"error": f"API error: {status_code or 'Unknown'}"}
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time

                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                return {"error": f"Request failed: {str(e)}"}

        return {"error": "Request failed after multiple attempts"}

    @cache_result(ttl=CACHE_TTL_INVENTORY)
    def get_products(self):
        """
        Get products using GraphQL with proper inventory data
        Returns format expected by inventory.py
        """
        query = """
        query getProducts($first: Int!, $after: String) {
            products(first: $first, after: $after) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        id
                        title
                        handle
                        variants(first: 10) {
                            edges {
                                node {
                                    id
                                    title
                                    sku
                                    price
                                    inventoryItem {
                                        inventoryLevels(first: 1) {
                                            edges {
                                                node {
                                                    quantities(names: ["available"]) {
                                                        name
                                                        quantity
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        """

        products = []
        cursor = None
        has_next_page = True

        # Paginate through all products
        while has_next_page:
            variables = {"first": 50}  # Smaller batches for better performance
            if cursor:
                variables["after"] = cursor
                
            data = self._make_graphql_request(query, variables)

            if "error" in data:
                return data  # Return error as-is

            if "errors" in data:
                return {"error": str(data["errors"])}

            products_data = data.get("data", {}).get("products", {})
            page_info = products_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            # Process products into format expected by inventory.py
            for edge in products_data.get("edges", []):
                try:
                    product = edge.get("node", {})
                    if not product:
                        continue

                    product_title = product.get("title", "Untitled Product")
                    product_handle = product.get("handle", "")

                    # Process variants
                    variants_data = product.get("variants", {})
                    if not isinstance(variants_data, dict):
                        continue

                    variant_edges = variants_data.get("edges", [])
                    if not variant_edges:
                        # Product with no variants
                        products.append({
                            "product": product_title,
                            "sku": "N/A",
                            "stock": 0,
                            "price": "$0.00",
                            "handle": product_handle
                        })
                        continue

                    # Process each variant
                    for variant_edge in variant_edges:
                        try:
                            variant = variant_edge.get("node", {})
                            if not variant:
                                continue

                            # Get basic variant info
                            sku = variant.get("sku") or "N/A"
                            price_value = variant.get("price") or "0.00"
                            price = f"${price_value}"
                            variant_title = variant.get("title", "Default")

                            # Get inventory quantity from new GraphQL structure
                            stock = 0
                            inventory_item = variant.get("inventoryItem")
                            if inventory_item and isinstance(inventory_item, dict):
                                inventory_levels = inventory_item.get("inventoryLevels", {})
                                if inventory_levels and isinstance(inventory_levels, dict):
                                    edges = inventory_levels.get("edges", [])
                                    if edges and len(edges) > 0:
                                        node = edges[0].get("node", {})
                                        if node and isinstance(node, dict):
                                            quantities = node.get("quantities", [])
                                            if quantities and isinstance(quantities, list):
                                                for q in quantities:
                                                    if (isinstance(q, dict) and 
                                                        q.get("name") == "available"):
                                                        stock = q.get("quantity", 0) or 0
                                                        break

                            # Create product entry in format expected by inventory.py
                            product_name = product_title
                            if variant_title != "Default" and variant_title != product_title:
                                product_name = f"{product_title} - {variant_title}"

                            products.append({
                                "product": product_name,
                                "sku": sku,
                                "stock": stock,
                                "price": price,
                                "handle": product_handle,
                                "variant_id": variant.get("id", "").replace("gid://shopify/ProductVariant/", "")
                            })
                            
                        except Exception as e:
                            logger.warning(f"Error processing variant: {e}")
                            continue
                            
                except Exception as e:
                    logger.warning(f"Error processing product: {e}")
                    continue

        return products

    @cache_result(ttl=CACHE_TTL_ORDERS)
    def get_orders(self, status="any", limit=50, start_date=None, end_date=None):
        """
        Get orders using GraphQL with proper data structure
        Returns consistent format for order_processing.py
        """
        # Build query filters
        query_filters = []
        
        if status != "any":
            if status == "paid":
                query_filters.append("financial_status:paid")
            elif status == "pending":
                query_filters.append("financial_status:pending")
            elif status == "refunded":
                query_filters.append("financial_status:refunded")
        
        # Add date filters if provided
        if start_date:
            if isinstance(start_date, str):
                query_filters.append(f"created_at:>={start_date}")
            else:
                query_filters.append(f"created_at:>={start_date.isoformat()}")
        
        if end_date:
            if isinstance(end_date, str):
                query_filters.append(f"created_at:<={end_date}")
            else:
                query_filters.append(f"created_at:<={end_date.isoformat()}")
        
        # Combine filters
        query_string = " AND ".join(query_filters) if query_filters else ""

        query = """
        query getOrders($first: Int!, $query: String) {
            orders(first: $first, query: $query, sortKey: CREATED_AT, reverse: true) {
                edges {
                    node {
                        id
                        name
                        email
                        displayFinancialStatus
                        displayFulfillmentStatus
                        createdAt
                        totalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        customer {
                            firstName
                            lastName
                            email
                        }
                        shippingAddress {
                            city
                            country
                            address1
                            zip
                        }
                        lineItems(first: 10) {
                            edges {
                                node {
                                    title
                                    quantity
                                    originalUnitPriceSet {
                                        shopMoney {
                                            amount
                                        }
                                    }
                                }
                            }
                        }
                        tags
                    }
                }
            }
        }
        """
        
        variables = {
            "first": min(limit, 250),
            "query": query_string if query_string else None
        }

        data = self._make_graphql_request(query, variables)
        
        if "error" in data:
            return data  # Return error as-is
            
        if "errors" in data:
            return {"error": str(data["errors"])}

        # Transform GraphQL response to format expected by order_processing.py
        orders = []
        orders_data = data.get("data", {}).get("orders", {}).get("edges", [])
        
        for edge in orders_data:
            node = edge.get("node", {})
            if not node:
                continue
                
            # Extract customer info safely
            customer_info = node.get("customer", {}) or {}
            first_name = customer_info.get("firstName", "") or ""
            last_name = customer_info.get("lastName", "") or ""
            customer_email = customer_info.get("email", "") or node.get("email", "")
            
            # Format customer display name
            if first_name or last_name:
                customer_display = f"{first_name} {last_name}".strip()
            else:
                customer_display = "Guest Customer"
            
            # Extract price safely
            total_price = "0.00"
            currency = "USD"
            price_set = node.get("totalPriceSet", {})
            if price_set and price_set.get("shopMoney"):
                shop_money = price_set.get("shopMoney", {})
                total_price = shop_money.get("amount", "0.00")
                currency = shop_money.get("currencyCode", "USD")
            
            # Extract line items
            line_items = []
            line_items_data = node.get("lineItems", {}).get("edges", [])
            for item_edge in line_items_data:
                item_node = item_edge.get("node", {})
                if item_node:
                    item_price = "0.00"
                    price_set = item_node.get("originalUnitPriceSet", {})
                    if price_set and price_set.get("shopMoney"):
                        item_price = price_set.get("shopMoney", {}).get("amount", "0.00")
                    
                    line_items.append({
                        "title": item_node.get("title", "Unknown Item"),
                        "quantity": item_node.get("quantity", 1),
                        "price": item_price
                    })

            # Create order object in format expected by order_processing.py
            order = {
                "id": node.get("id", "").replace("gid://shopify/Order/", ""),
                "order_number": node.get("name", "").replace("#", ""),
                "name": node.get("name", ""),
                "email": customer_email,
                "total_price": total_price,
                "currency": currency,
                "financial_status": node.get("displayFinancialStatus", "unknown").lower(),
                "fulfillment_status": node.get("displayFulfillmentStatus", "unfulfilled").lower(),
                "created_at": node.get("createdAt", ""),
                "customer": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": customer_email
                },
                "shipping_address": node.get("shippingAddress", {}),
                "line_items": line_items,
                "tags": node.get("tags", ""),
                "gateway": "unknown",  # Gateway not available in GraphQL API
                "risk_level": "low"  # Default for now
            }
            orders.append(order)
            
        return orders

    def _handle_protected_data_error(self, error_response):
        """Handle Protected Customer Data program errors"""
        if isinstance(error_response, dict) and "error" in error_response:
            error_msg = error_response["error"].lower()
            if "protected customer data" in error_msg or "customer data access" in error_msg:
                return {
                    "error": "Customer data access restricted by Shopify's Protected Customer Data program",
                    "protected_data_error": True,
                    "suggestion": "This app complies with data protection policies. Some customer details may be limited."
                }
        return error_response

    def register_webhooks(self):
        """
        Automatically register essential webhooks using GraphQL:
        - app/uninstalled: Vital for database scrubbing
        """
        webhook_url = f"{os.getenv('SHOPIFY_APP_URL', 'https://employeesuite-production.onrender.com')}/webhooks/app/uninstall"
        
        mutation = """
        mutation webhookSubscriptionCreate($topic: WebhookSubscriptionTopic!, $webhookSubscription: WebhookSubscriptionInput!) {
          webhookSubscriptionCreate(topic: $topic, webhookSubscription: $webhookSubscription) {
            userErrors {
              field
              message
            }
            webhookSubscription {
              id
            }
          }
        }
        """
        
        variables = {
            "topic": "APP_UNINSTALLED",
            "webhookSubscription": {
                "callbackUrl": webhook_url,
                "format": "JSON"
            }
        }
        
        logger.info(f"🔄 Registering app/uninstalled webhook for {self.shop_url}...")
        result = self._make_graphql_request(mutation, variables)
        
        if "error" in result:
            logger.error(f"❌ Webhook registration failed for {self.shop_url}: {result['error']}")
            return False
            
        user_errors = result.get("data", {}).get("webhookSubscriptionCreate", {}).get("userErrors", [])
        if user_errors:
            # Check if it already exists (Shopify returns an error if already registered)
            for error in user_errors:
                if "already" in error.get("message", "").lower():
                    logger.info(f"✅ Webhook already registered for {self.shop_url}")
                    return True
            logger.error(f"❌ Webhook User Errors: {user_errors}")
            return False
            
        logger.info(f"✅ Webhook registered successfully for {self.shop_url}")
        return True

    @staticmethod
    def verify_hmac(params, hmac_to_verify):
        """
        SECURE: Verify Shopify HMAC to ensure requests to registration helpers are authentic.
        Used when registration is triggered via a link or non-webhook callback.
        """
        import hmac
        import hashlib
        from config import SHOPIFY_API_SECRET
        
        if not SHOPIFY_API_SECRET or not hmac_to_verify:
            return False
            
        # 1. Remove hmac and signature from params
        data_params = {k: v for k, v in params.items() if k not in ["hmac", "signature"]}
        
        # 2. Sort and join
        # Shopify sorts alphabetically by key
        sorted_params = sorted(data_params.items())
        message = "&".join([f"{k}={v}" for k, v in sorted_params])
        
        # 3. Compute HMAC
        calculated_hmac = hmac.new(
            SHOPIFY_API_SECRET.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(calculated_hmac, hmac_to_verify)

    def get_low_stock(self, threshold=5):
        inventory = self.get_products()
        if isinstance(inventory, dict) and "error" in inventory:
            return inventory
        return [item for item in inventory if item["stock"] < threshold]


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    SHOP_URL = os.getenv("SHOPIFY_URL", "testsuite-dev.myshopify.com")
    ACCESS_TOKEN = os.getenv("SHOPIFY_TOKEN", "")
    if not ACCESS_TOKEN:
        print("No SHOPIFY_TOKEN found in .env file!")
        exit(1)
    print(f"Testing connection to {SHOP_URL}...")
    client = ShopifyClient(SHOP_URL, ACCESS_TOKEN)
    print("\nTesting inventory...")
    inventory = client.get_products()
    if isinstance(inventory, dict) and "error" in inventory:
        print(f"Error: {inventory['error']}")
    else:
        print(f"Found {len(inventory)} products")
        for item in inventory[:3]:
            print(f"  - {item['product']}: {item['stock']} units at {item['price']}")
    print("\nTesting orders...")
    orders = client.get_orders()
    if isinstance(orders, dict) and "error" in orders:
        print(f"Error: {orders['error']}")
    else:
        print(f"Found {len(orders)} orders")
    print("\nTesting low stock...")
    low_stock = client.get_low_stock(threshold=10)
    if isinstance(low_stock, dict) and "error" in low_stock:
        print(f"Error: {low_stock['error']}")
    else:
        print(f"Found {len(low_stock)} low stock items")
