"""
Shopify GraphQL API Client
Bypasses REST API restrictions on protected customer data
"""

import requests
import logging
from typing import Dict, List, Optional, Any
from config import SHOPIFY_API_VERSION

logger = logging.getLogger(__name__)

class ShopifyGraphQLClient:
    """GraphQL client for Shopify Admin API"""
    
    def __init__(self, shop_url: str, access_token: str):
        """
        Initialize GraphQL client
        
        Args:
            shop_url: Shop domain (e.g., 'mystore.myshopify.com')
            access_token: Shopify access token
        """
        self.shop_url = shop_url.replace('https://', '').replace('http://', '')
        self.access_token = access_token
        self.api_version = SHOPIFY_API_VERSION
        self.endpoint = f"https://{self.shop_url}/admin/api/{self.api_version}/graphql.json"
        
    def execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Execute a GraphQL query
        
        Args:
            query: GraphQL query string
            variables: Optional query variables
            
        Returns:
            GraphQL response data
        """
        headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': self.access_token
        }
        
        payload = {'query': query}
        if variables:
            payload['variables'] = variables
            
        try:
            response = requests.post(
                self.endpoint,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for GraphQL errors
            if 'errors' in data:
                error_msg = '; '.join([e.get('message', 'Unknown error') for e in data['errors']])
                logger.error(f"GraphQL errors: {error_msg}")
                return {'error': error_msg}
            
            return data.get('data', {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"GraphQL request failed: {e}")
            return {'error': str(e)}
    
    def get_orders(self, limit: int = 250, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch orders using GraphQL (bypasses REST API restrictions)
        
        Args:
            limit: Number of orders to fetch (max 250)
            cursor: Pagination cursor for next page
            
        Returns:
            Orders data with pagination info
        """
        query = """
        query GetOrders($first: Int!, $after: String) {
          orders(first: $first, after: $after, sortKey: CREATED_AT, reverse: true) {
            edges {
              cursor
              node {
                id
                name
                createdAt
                displayFinancialStatus
                displayFulfillmentStatus
                totalPriceSet {
                  shopMoney {
                    amount
                    currencyCode
                  }
                }
                lineItems(first: 250) {
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
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        variables = {
            'first': min(limit, 250),
            'after': cursor
        }
        
        return self.execute_query(query, variables)
    
    def get_products(self, limit: int = 250, cursor: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetch products with inventory using GraphQL
        
        Args:
            limit: Number of products to fetch (max 250)
            cursor: Pagination cursor
            
        Returns:
            Products data with inventory levels
        """
        query = """
        query GetProducts($first: Int!, $after: String) {
          products(first: $first, after: $after) {
            edges {
              cursor
              node {
                id
                title
                status
                totalInventory
                variants(first: 100) {
                  edges {
                    node {
                      id
                      title
                      sku
                      price
                      inventoryQuantity
                    }
                  }
                }
              }
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        """
        
        variables = {
            'first': min(limit, 250),
            'after': cursor
        }
        
        return self.execute_query(query, variables)
    
    def get_all_orders(self, max_orders: Optional[int] = None) -> List[Dict]:
        """
        Fetch all orders with automatic pagination
        
        Args:
            max_orders: Optional limit on total orders to fetch
            
        Returns:
            List of all orders
        """
        all_orders = []
        cursor = None
        has_next_page = True
        
        while has_next_page:
            if max_orders and len(all_orders) >= max_orders:
                break
                
            result = self.get_orders(limit=250, cursor=cursor)
            
            if 'error' in result:
                logger.error(f"Failed to fetch orders: {result['error']}")
                break
            
            orders_data = result.get('orders', {})
            edges = orders_data.get('edges', [])
            
            for edge in edges:
                all_orders.append(edge['node'])
                
            page_info = orders_data.get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor')
            
            logger.info(f"Fetched {len(edges)} orders, total: {len(all_orders)}")
            
        return all_orders
    
    def get_all_products(self) -> List[Dict]:
        """
        Fetch all products with automatic pagination
        
        Returns:
            List of all products with inventory
        """
        all_products = []
        cursor = None
        has_next_page = True
        
        while has_next_page:
            result = self.get_products(limit=250, cursor=cursor)
            
            if 'error' in result:
                logger.error(f"Failed to fetch products: {result['error']}")
                break
            
            products_data = result.get('products', {})
            edges = products_data.get('edges', [])
            
            for edge in edges:
                all_products.append(edge['node'])
                
            page_info = products_data.get('pageInfo', {})
            has_next_page = page_info.get('hasNextPage', False)
            cursor = page_info.get('endCursor')
            
            logger.info(f"Fetched {len(edges)} products, total: {len(all_products)}")
            
        return all_products
