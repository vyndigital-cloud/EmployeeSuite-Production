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

        # Handle encrypted tokens with graceful failure
        if access_token and not (
            access_token.startswith("shpat_") or access_token.startswith("shpca_")
        ):
            try:
                from data_encryption import decrypt_access_token

                decrypted = decrypt_access_token(access_token)
                if decrypted:
                    self.access_token = decrypted
                else:
                    logger.warning(
                        f"Token decryption failed for {shop_url} - store needs reconnection"
                    )
                    self.access_token = None  # Force reconnection
            except Exception as e:
                logger.error(f"Token handling failed for {shop_url}: {e}")
                self.access_token = None  # Force reconnection
        else:
            self.access_token = access_token
        self.api_version = SHOPIFY_API_VERSION  # Match app.json API version

        # Debug logging: Verify token format
        if access_token:
            token_preview = (
                access_token[:10] if len(access_token) > 10 else access_token
            )
            token_length = len(access_token)
            starts_with_shpat = (
                access_token.startswith("shpat_") if access_token else False
            )
            starts_with_shpca = (
                access_token.startswith("shpca_") if access_token else False
            )

            logger.info(
                f"ShopifyClient initialized with token: {token_preview}... (length: {token_length}, starts with shpat_: {starts_with_shpat}, starts with shpca_: {starts_with_shpca})"
            )

            if not (starts_with_shpat or starts_with_shpca):
                logger.warning(
                    f"WARNING: Access token doesn't match expected format! Token starts with: {access_token[:20]}"
                )
        else:
            logger.error("ShopifyClient initialized with None/empty access_token!")

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
                        response_text = response.text[
                            :500
                        ]  # Get first 500 chars for logging
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
                        response_text = response.text[
                            :500
                        ]  # Get first 500 chars for logging
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
                        response_text = response.text[
                            :500
                        ]  # Get first 500 chars for logging
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
                        response_text = response.text[
                            :500
                        ]  # Get first 500 chars for logging
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
        Get products using GraphQL (migrated from deprecated REST API)
        Returns same format as before for backward compatibility
        """
        # GraphQL query to fetch products with variants and inventory
        # Migrated from deprecated REST API /products.json endpoint
        # Using GraphQL Admin API as required by Shopify (deadline: 2025-04-01)
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
                        variants(first: 250) {
                            edges {
                                node {
                                    id
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

        inventory = []
        cursor = None
        has_next_page = True

        # Paginate through all products
        while has_next_page:
            variables = {"first": 250}  # Max 250 products per request
            if cursor:
                variables["after"] = cursor
            data = self._make_graphql_request(query, variables)

            if "error" in data:
                return self._handle_protected_data_error(data)

            if "errors" in data:
                return {"error": str(data["errors"])}

            products_data = data.get("data", {}).get("products", {})
            page_info = products_data.get("pageInfo", {})
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")

            # Process products
            for edge in products_data.get("edges", []):
                try:
                    product = edge.get("node", {})
                    if not product:
                        continue

                    product_title = product.get("title", "Untitled")

                    # Process variants - handle cases where variants might be None or missing
                    variants_data = product.get("variants", {})
                    if not isinstance(variants_data, dict):
                        # If no variants, skip this product
                        continue

                    variant_edges = variants_data.get("edges", [])
                    if not variant_edges:
                        # Product with no variants - still add it with default values
                        inventory.append(
                            {
                                "product": product_title,
                                "sku": "N/A",
                                "stock": 0,
                                "price": "N/A",
                            }
                        )
                        continue

                    # Process each variant
                    for variant_edge in variant_edges:
                        try:
                            variant = variant_edge.get("node", {})
                            if not variant:
                                continue

                            # Handle None values - Shopify can return None for SKU
                            sku = variant.get("sku") or "N/A"
                            price_value = variant.get("price") or "0"
                            price = f"${price_value}" if price_value != "0" else "N/A"

                            # Get inventory quantity from GraphQL structure
                            # CRITICAL: Shopify changed to quantities array structure
                            # quantities(names: ["available"]) returns array with {name, quantity}
                            stock = 0
                            inventory_item = variant.get("inventoryItem")
                            if inventory_item and isinstance(inventory_item, dict):
                                inventory_levels = inventory_item.get(
                                    "inventoryLevels", {}
                                )
                                if inventory_levels and isinstance(
                                    inventory_levels, dict
                                ):
                                    edges = inventory_levels.get("edges", [])
                                    if edges and len(edges) > 0:
                                        node = edges[0].get("node", {})
                                        if node and isinstance(node, dict):
                                            # Parse quantities array: [{"name": "available", "quantity": 10}]
                                            quantities = node.get("quantities", [])
                                            if quantities and isinstance(
                                                quantities, list
                                            ):
                                                # Find the "available" quantity
                                                for q in quantities:
                                                    if (
                                                        isinstance(q, dict)
                                                        and q.get("name") == "available"
                                                    ):
                                                        stock = (
                                                            q.get("quantity", 0) or 0
                                                        )
                                                        break

                            inventory.append(
                                {
                                    "product": product_title,
                                    "sku": sku,
                                    "stock": stock,
                                    "price": price,
                                }
                            )
                        except Exception as e:
                            # Skip this variant if there's an error, continue with others
                            continue
                except Exception as e:
                    # Skip this product if there's an error, continue with others
                    continue

        return inventory

    @cache_result(ttl=60)  # Reduced to 1 minute for customer data compliance
    def get_orders(self, status="any", limit=50):
        """
        Get orders using GraphQL (migrated from legacy REST API)
        Avoids "Protected Customer Data" 403 errors by using more granular GraphQL permissions
        """
        # Map REST status to GraphQL query filter
        query_filter = ""
        if status != "any":
            # GraphQL uses specific query syntax
            # financial_status:paid, etc.
            if status == "paid":
                query_filter = "query: \"financial_status:paid\""
            elif status == "pending":
                query_filter = "query: \"financial_status:pending\""
            elif status == "refunded":
                query_filter = "query: \"financial_status:refunded\""

        query = """
        query getOrders($first: Int!, $query: String) {
            orders(first: $first, query: $query, sortKey: CREATED_AT, reverse: true) {
                edges {
                    node {
                        name
                        id
                        displayFinancialStatus
                        currentTotalPriceSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                        customer {
                            email
                            firstName
                            lastName
                        }
                        lineItems(first: 5) {
                            edges {
                                node {
                                    title
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        
        variables = {
            "first": min(limit, 50), # Max 50 for performance
            "query": query_filter.replace("query: ", "").replace("\"", "") if query_filter else None
        }

        data = self._make_graphql_request(query, variables)
        
        if "error" in data:
            return self._handle_protected_data_error(data)
            
        if "errors" in data:
             return {"error": str(data["errors"])}

        orders = []
        orders_data = data.get("data", {}).get("orders", {}).get("edges", [])
        
        for edge in orders_data:
            node = edge.get("node", {})
            if not node:
                continue
                
            # GDPR-compliant customer display - no email exposure
            customer_display = "Guest"
            if node.get("customer"):
                customer = node.get("customer", {})
                first_name = customer.get("firstName", "")
                last_name = customer.get("lastName", "")
                if first_name or last_name:
                    customer_display = f"{first_name} {last_name}".strip()
                else:
                    customer_display = "Customer"
                
            # Safely extract price
            price = "0.00"
            if node.get("currentTotalPriceSet") and node.get("currentTotalPriceSet").get("shopMoney"):
                price = node.get("currentTotalPriceSet").get("shopMoney").get("amount", "0.00")
            
            # Count items
            item_count = 0
            if node.get("lineItems"):
                item_count = len(node.get("lineItems", {}).get("edges", []))

            orders.append(
                {
                    "id": node.get("name", "Unknown"), # Use name (e.g. #1001) as ID for display
                    "customer": customer_display,
                    "total": f"${price}",
                    "items": item_count,
                    "status": node.get("displayFinancialStatus", "N/A"),
                }
            )
            
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
