import requests
import os
from performance import cache_result, CACHE_TTL_INVENTORY, CACHE_TTL_ORDERS

class ShopifyClient:
    def __init__(self, shop_url, access_token):
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = "2024-10"  # Match app.json API version
        
    def _get_headers(self):
        return {
            "X-Shopify-Access-Token": self.access_token,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint, retries=3):
        """
        Make API request with automatic retry logic (professional standard)
        Retries on network errors with exponential backoff
        """
        url = f"https://{self.shop_url}/admin/api/{self.api_version}/{endpoint}"
        headers = self._get_headers()
        headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        headers['Pragma'] = 'no-cache'
        headers['Expires'] = '0'
        
        for attempt in range(retries):
            try:
                response = requests.get(url, headers=headers, timeout=10)  # Reduced for faster failures
                # CRITICAL: Check status code BEFORE raise_for_status to handle 403 properly
                status_code = response.status_code
                if status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            errors = error_data.get('errors', {})
                            if isinstance(errors, dict):
                                error_detail = errors.get('base', [error_detail])
                                if isinstance(error_detail, list):
                                    error_detail = error_detail[0] if error_detail else "Access denied - Missing required permissions"
                            elif isinstance(errors, str):
                                error_detail = errors
                        elif isinstance(error_data, str):
                            error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": f"{error_detail} - Check your app permissions", "permission_denied": True}
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time
                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                return {"error": "Request timeout - Shopify API is taking too long to respond"}
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time
                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                return {"error": "Connection error - Cannot connect to Shopify. Check your internet connection."}
            except requests.exceptions.HTTPError as e:
                # CRITICAL: Handle HTTP errors with proper error extraction
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                
                # Don't retry on HTTP errors (4xx, 5xx) - these are permanent
                if status_code == 401:
                    # Authentication failed - token may be expired or revoked
                    error_detail = "Authentication failed"
                    try:
                        if hasattr(e, 'response') and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = error_data.get('errors', {}).get('base', [error_detail])
                                if isinstance(error_detail, list):
                                    error_detail = error_detail[0] if error_detail else "Authentication failed"
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": f"{error_detail} - Please reconnect your store", "auth_failed": True}
                elif status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    try:
                        if hasattr(e, 'response') and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                errors = error_data.get('errors', {})
                                if isinstance(errors, dict):
                                    error_detail = errors.get('base', [error_detail])
                                    if isinstance(error_detail, list):
                                        error_detail = error_detail[0] if error_detail else "Access denied - Missing required permissions"
                                elif isinstance(errors, str):
                                    error_detail = errors
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": f"{error_detail} - Check your app permissions", "permission_denied": True}
                elif status_code == 429:
                    # Rate limit - wait but not too long
                    if attempt < retries - 1:
                        import time
                        time.sleep(min(2, 1 * (attempt + 1)))  # Max 2 seconds
                        continue
                    return {"error": "Rate limit exceeded - Please wait a moment and try again"}
                elif status_code:
                    error_detail = f"API error: {status_code}"
                    try:
                        if hasattr(e, 'response') and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = str(error_data.get('errors', error_detail))
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
    
    def _make_graphql_request(self, query, variables=None, retries=3):
        """
        Make GraphQL request with automatic retry logic (professional standard)
        Retries on network errors with exponential backoff
        """
        url = f"https://{self.shop_url}/admin/api/{self.api_version}/graphql.json"
        headers = self._get_headers()
        headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        for attempt in range(retries):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=10)  # Reduced from 15s for faster failures
                # CRITICAL: Check status code BEFORE raise_for_status to handle 403 properly
                status_code = response.status_code
                if status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    try:
                        error_data = response.json()
                        if isinstance(error_data, dict):
                            errors = error_data.get('errors', {})
                            if isinstance(errors, dict):
                                error_detail = errors.get('base', [error_detail])
                                if isinstance(error_detail, list):
                                    error_detail = error_detail[0] if error_detail else "Access denied - Missing required permissions"
                            elif isinstance(errors, str):
                                error_detail = errors
                        elif isinstance(error_data, str):
                            error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": f"{error_detail} - Check your app permissions", "permission_denied": True}
                response.raise_for_status()
                return response.json()
            except requests.exceptions.Timeout:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time
                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                return {"error": "Request timeout - Shopify API is taking too long to respond"}
            except requests.exceptions.ConnectionError:
                if attempt < retries - 1:
                    # Faster retries - max 0.5s delay
                    import time
                    time.sleep(min(0.5, 0.2 * (attempt + 1)))
                    continue
                return {"error": "Connection error - Cannot connect to Shopify. Check your internet connection."}
            except requests.exceptions.HTTPError as e:
                # CRITICAL: Handle HTTP errors with proper error extraction
                status_code = e.response.status_code if hasattr(e, 'response') and e.response else None
                
                # Don't retry on HTTP errors (4xx, 5xx) - these are permanent
                if status_code == 401:
                    # Authentication failed - token may be expired or revoked
                    error_detail = "Authentication failed"
                    try:
                        if hasattr(e, 'response') and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = error_data.get('errors', {}).get('base', [error_detail])
                                if isinstance(error_detail, list):
                                    error_detail = error_detail[0] if error_detail else "Authentication failed"
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": f"{error_detail} - Please reconnect your store", "auth_failed": True}
                elif status_code == 403:
                    # Permission denied - missing scopes
                    error_detail = "Access denied - Missing required permissions"
                    try:
                        if hasattr(e, 'response') and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                errors = error_data.get('errors', {})
                                if isinstance(errors, dict):
                                    error_detail = errors.get('base', [error_detail])
                                    if isinstance(error_detail, list):
                                        error_detail = error_detail[0] if error_detail else "Access denied - Missing required permissions"
                                elif isinstance(errors, str):
                                    error_detail = errors
                            elif isinstance(error_data, str):
                                error_detail = error_data
                    except (ValueError, AttributeError, TypeError):
                        pass
                    return {"error": f"{error_detail} - Check your app permissions", "permission_denied": True}
                elif status_code == 429:
                    # Rate limit - wait but not too long
                    if attempt < retries - 1:
                        import time
                        time.sleep(min(2, 1 * (attempt + 1)))  # Max 2 seconds
                        continue
                    return {"error": "Rate limit exceeded - Please wait a moment and try again"}
                elif status_code:
                    error_detail = f"API error: {status_code}"
                    try:
                        if hasattr(e, 'response') and e.response:
                            error_data = e.response.json()
                            if isinstance(error_data, dict):
                                error_detail = str(error_data.get('errors', error_detail))
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
                                        id
                                        quantityAvailable
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
                return {"error": data["error"]}
            
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
                        inventory.append({
                            'product': product_title,
                            'sku': 'N/A',
                            'stock': 0,
                            'price': 'N/A'
                        })
                        continue
                    
                    # Process each variant
                    for variant_edge in variant_edges:
                        try:
                            variant = variant_edge.get("node", {})
                            if not variant:
                                continue
                            
                            # Handle None values - Shopify can return None for SKU
                            sku = variant.get("sku") or 'N/A'
                            price_value = variant.get("price") or '0'
                            price = f"${price_value}" if price_value != '0' else 'N/A'
                            
                            # Get inventory quantity from GraphQL structure
                            stock = 0
                            inventory_item = variant.get("inventoryItem")
                            if inventory_item and isinstance(inventory_item, dict):
                                # Use quantityAvailable (direct field, more reliable)
                                stock = inventory_item.get("quantityAvailable", 0) or 0
                            
                            inventory.append({
                                'product': product_title,
                                'sku': sku,
                                'stock': stock,
                                'price': price
                            })
                        except Exception as e:
                            # Skip this variant if there's an error, continue with others
                            continue
                except Exception as e:
                    # Skip this product if there's an error, continue with others
                    continue
        
        return inventory
    
    @cache_result(ttl=CACHE_TTL_ORDERS)
    def get_orders(self, status='any', limit=50):
        data = self._make_request(f"orders.json?status={status}&limit={limit}")
        if "error" in data:
            return {"error": data["error"]}
        orders = []
        for order in data.get('orders', []):
            orders.append({
                'id': order['order_number'],
                'customer': order.get('customer', {}).get('email', 'Guest'),
                'total': f"${order['total_price']}",
                'items': len(order['line_items']),
                'status': order.get('financial_status', 'N/A').upper()
            })
        return orders
    
    def get_low_stock(self, threshold=5):
        inventory = self.get_products()
        if isinstance(inventory, dict) and "error" in inventory:
            return inventory
        return [item for item in inventory if item['stock'] < threshold]

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    SHOP_URL = os.getenv('SHOPIFY_URL', 'testsuite-dev.myshopify.com')
    ACCESS_TOKEN = os.getenv('SHOPIFY_TOKEN', '')
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
