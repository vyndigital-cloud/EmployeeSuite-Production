"""
Shopify Metafields Support - Production Ready
Implements proper metafields management for Shopify apps
"""
import json
import logging
import requests
from flask import Blueprint, request, jsonify
from models import db, ShopifyStore
from logging_config import logger

metafields_bp = Blueprint('metafields', __name__)

class ShopifyMetafields:
    """
    Shopify Metafields Management Class
    Handles CRUD operations for Shopify metafields
    """
    
    def __init__(self, shop_domain, access_token):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.api_version = "2025-10"
        self.base_url = f"https://{shop_domain}/admin/api/{self.api_version}"
    
    def get_headers(self):
        """Get API headers for requests"""
        return {
            'X-Shopify-Access-Token': self.access_token,
            'Content-Type': 'application/json'
        }
    
    def get_metafields(self, owner_type, owner_id, namespace=None, key=None):
        """
        Get metafields for a specific owner
        
        Args:
            owner_type: 'product', 'variant', 'order', 'customer', 'shop', etc.
            owner_id: ID of the owner resource
            namespace: Optional namespace filter
            key: Optional key filter
        """
        try:
            url = f"{self.base_url}/{owner_type}s/{owner_id}/metafields.json"
            
            params = {}
            if namespace:
                params['namespace'] = namespace
            if key:
                params['key'] = key
            
            response = requests.get(url, headers=self.get_headers(), params=params)
            
            if response.status_code == 200:
                metafields = response.json().get('metafields', [])
                logger.info(f"Retrieved {len(metafields)} metafields for {owner_type} {owner_id}")
                return metafields
            else:
                logger.error(f"Failed to get metafields: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting metafields: {e}")
            return None
    
    def create_metafield(self, owner_type, owner_id, namespace, key, value, value_type="string", description=None):
        """
        Create a new metafield
        
        Args:
            owner_type: 'product', 'variant', 'order', 'customer', 'shop', etc.
            owner_id: ID of the owner resource
            namespace: Namespace for the metafield
            key: Key for the metafield
            value: Value for the metafield
            value_type: Type of value (string, integer, json_string, etc.)
            description: Optional description
        """
        try:
            url = f"{self.base_url}/{owner_type}s/{owner_id}/metafields.json"
            
            metafield_data = {
                "metafield": {
                    "namespace": namespace,
                    "key": key,
                    "value": str(value),
                    "type": value_type
                }
            }
            
            if description:
                metafield_data["metafield"]["description"] = description
            
            response = requests.post(url, json=metafield_data, headers=self.get_headers())
            
            if response.status_code == 201:
                metafield = response.json().get('metafield')
                logger.info(f"Created metafield {namespace}.{key} for {owner_type} {owner_id}")
                return metafield
            else:
                logger.error(f"Failed to create metafield: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating metafield: {e}")
            return None
    
    def update_metafield(self, metafield_id, value, value_type=None):
        """
        Update an existing metafield
        
        Args:
            metafield_id: ID of the metafield to update
            value: New value
            value_type: Optional new value type
        """
        try:
            url = f"{self.base_url}/metafields/{metafield_id}.json"
            
            update_data = {
                "metafield": {
                    "value": str(value)
                }
            }
            
            if value_type:
                update_data["metafield"]["type"] = value_type
            
            response = requests.put(url, json=update_data, headers=self.get_headers())
            
            if response.status_code == 200:
                metafield = response.json().get('metafield')
                logger.info(f"Updated metafield {metafield_id}")
                return metafield
            else:
                logger.error(f"Failed to update metafield: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error updating metafield: {e}")
            return None
    
    def delete_metafield(self, metafield_id):
        """
        Delete a metafield
        
        Args:
            metafield_id: ID of the metafield to delete
        """
        try:
            url = f"{self.base_url}/metafields/{metafield_id}.json"
            
            response = requests.delete(url, headers=self.get_headers())
            
            if response.status_code == 200:
                logger.info(f"Deleted metafield {metafield_id}")
                return True
            else:
                logger.error(f"Failed to delete metafield: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting metafield: {e}")
            return False
    
    def get_shop_metafields(self, namespace=None):
        """
        Get shop-level metafields
        
        Args:
            namespace: Optional namespace filter
        """
        try:
            url = f"{self.base_url}/metafields.json"
            
            params = {}
            if namespace:
                params['namespace'] = namespace
            
            response = requests.get(url, headers=self.get_headers(), params=params)
            
            if response.status_code == 200:
                metafields = response.json().get('metafields', [])
                logger.info(f"Retrieved {len(metafields)} shop metafields")
                return metafields
            else:
                logger.error(f"Failed to get shop metafields: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting shop metafields: {e}")
            return None
    
    def bulk_update_metafields(self, metafields):
        """
        Bulk update multiple metafields
        
        Args:
            metafields: List of metafield objects with id and value
        """
        try:
            updated_count = 0
            
            for metafield in metafields:
                metafield_id = metafield.get('id')
                value = metafield.get('value')
                value_type = metafield.get('type')
                
                if self.update_metafield(metafield_id, value, value_type):
                    updated_count += 1
            
            logger.info(f"Bulk updated {updated_count}/{len(metafields)} metafields")
            return updated_count
            
        except Exception as e:
            logger.error(f"Error in bulk update: {e}")
            return 0

# Employee Suite specific metafield operations
class EmployeeSuiteMetafields(ShopifyMetafields):
    """
    Employee Suite specific metafield operations
    """
    
    NAMESPACE = "employeesuite"
    
    def __init__(self, shop_domain, access_token):
        super().__init__(shop_domain, access_token)
    
    def store_inventory_settings(self, settings):
        """
        Store inventory management settings
        
        Args:
            settings: Dictionary of inventory settings
        """
        return self.create_metafield(
            "shop", 
            self.shop_domain,
            self.NAMESPACE,
            "inventory_settings",
            json.dumps(settings),
            "json_string",
            "Employee Suite inventory management settings"
        )
    
    def get_inventory_settings(self):
        """
        Get inventory management settings
        """
        metafields = self.get_shop_metafields(self.NAMESPACE)
        if metafields:
            for metafield in metafields:
                if metafield.get('key') == 'inventory_settings':
                    return json.loads(metafield.get('value', '{}'))
        return {}
    
    def store_analytics_preferences(self, preferences):
        """
        Store analytics preferences
        
        Args:
            preferences: Dictionary of analytics preferences
        """
        return self.create_metafield(
            "shop",
            self.shop_domain,
            self.NAMESPACE,
            "analytics_preferences",
            json.dumps(preferences),
            "json_string",
            "Employee Suite analytics preferences"
        )
    
    def get_analytics_preferences(self):
        """
        Get analytics preferences
        """
        metafields = self.get_shop_metafields(self.NAMESPACE)
        if metafields:
            for metafield in metafields:
                if metafield.get('key') == 'analytics_preferences':
                    return json.loads(metafield.get('value', '{}'))
        return {}
    
    def store_product_notes(self, product_id, notes):
        """
        Store notes for a specific product
        
        Args:
            product_id: Shopify product ID
            notes: Product notes string
        """
        return self.create_metafield(
            "product",
            product_id,
            self.NAMESPACE,
            "notes",
            notes,
            "multi_line_text_field",
            "Employee Suite product notes"
        )
    
    def get_product_notes(self, product_id):
        """
        Get notes for a specific product
        """
        metafields = self.get_metafields("product", product_id, self.NAMESPACE, "notes")
        if metafields and len(metafields) > 0:
            return metafields[0].get('value', '')
        return ""
    
    def store_custom_field(self, owner_type, owner_id, field_name, value, field_type="string"):
        """
        Store a custom field for any resource
        
        Args:
            owner_type: Type of resource (product, order, etc.)
            owner_id: ID of the resource
            field_name: Name of the custom field
            value: Field value
            field_type: Type of value
        """
        return self.create_metafield(
            owner_type,
            owner_id,
            self.NAMESPACE,
            field_name,
            value,
            field_type,
            f"Employee Suite custom field: {field_name}"
        )
    
    def get_custom_field(self, owner_type, owner_id, field_name):
        """
        Get a custom field value
        
        Args:
            owner_type: Type of resource
            owner_id: ID of the resource
            field_name: Name of the custom field
        """
        metafields = self.get_metafields(owner_type, owner_id, self.NAMESPACE, field_name)
        if metafields and len(metafields) > 0:
            return metafields[0].get('value')
        return None

# API Routes
@metafields_bp.route('/api/metafields/shop', methods=['GET'])
def get_shop_metafields():
    """
    Get shop-level metafields
    """
    try:
        shop = request.args.get('shop')
        if not shop:
            return jsonify({'error': 'Missing shop parameter'}), 400
        
        store = ShopifyStore.query.filter_by(shop_domain=shop).first()
        if not store or not store.access_token:
            return jsonify({'error': 'Store not found or no access token'}), 404
        
        metafields_manager = EmployeeSuiteMetafields(shop, store.access_token)
        metafields = metafields_manager.get_shop_metafields()
        
        return jsonify({
            'success': True,
            'metafields': metafields
        })
        
    except Exception as e:
        logger.error(f"Error getting shop metafields: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@metafields_bp.route('/api/metafields/product/<int:product_id>', methods=['GET'])
def get_product_metafields(product_id):
    """
    Get metafields for a specific product
    """
    try:
        shop = request.args.get('shop')
        if not shop:
            return jsonify({'error': 'Missing shop parameter'}), 400
        
        store = ShopifyStore.query.filter_by(shop_domain=shop).first()
        if not store or not store.access_token:
            return jsonify({'error': 'Store not found or no access token'}), 404
        
        metafields_manager = EmployeeSuiteMetafields(shop, store.access_token)
        metafields = metafields_manager.get_metafields("product", product_id)
        
        return jsonify({
            'success': True,
            'metafields': metafields
        })
        
    except Exception as e:
        logger.error(f"Error getting product metafields: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@metafields_bp.route('/api/metafields/product/<int:product_id>/notes', methods=['POST'])
def update_product_notes(product_id):
    """
    Update notes for a product
    """
    try:
        shop = request.args.get('shop')
        data = request.get_json()
        
        if not shop:
            return jsonify({'error': 'Missing shop parameter'}), 400
        
        notes = data.get('notes', '')
        
        store = ShopifyStore.query.filter_by(shop_domain=shop).first()
        if not store or not store.access_token:
            return jsonify({'error': 'Store not found or no access token'}), 404
        
        metafields_manager = EmployeeSuiteMetafields(shop, store.access_token)
        
        # Check if notes metafield already exists
        existing_metafields = metafields_manager.get_metafields("product", product_id, metafields_manager.NAMESPACE, "notes")
        
        if existing_metafields and len(existing_metafields) > 0:
            # Update existing metafield
            metafield_id = existing_metafields[0].get('id')
            result = metafields_manager.update_metafield(metafield_id, notes, "multi_line_text_field")
        else:
            # Create new metafield
            result = metafields_manager.store_product_notes(product_id, notes)
        
        if result:
            return jsonify({
                'success': True,
                'message': 'Product notes updated successfully'
            })
        else:
            return jsonify({'error': 'Failed to update product notes'}), 500
        
    except Exception as e:
        logger.error(f"Error updating product notes: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@metafields_bp.route('/api/metafields/inventory-settings', methods=['GET', 'POST'])
def inventory_settings():
    """
    Get or update inventory settings
    """
    try:
        shop = request.args.get('shop')
        if not shop:
            return jsonify({'error': 'Missing shop parameter'}), 400
        
        store = ShopifyStore.query.filter_by(shop_domain=shop).first()
        if not store or not store.access_token:
            return jsonify({'error': 'Store not found or no access token'}), 404
        
        metafields_manager = EmployeeSuiteMetafields(shop, store.access_token)
        
        if request.method == 'GET':
            settings = metafields_manager.get_inventory_settings()
            return jsonify({
                'success': True,
                'settings': settings
            })
        
        elif request.method == 'POST':
            data = request.get_json()
            settings = data.get('settings', {})
            
            result = metafields_manager.store_inventory_settings(settings)
            
            if result:
                return jsonify({
                    'success': True,
                    'message': 'Inventory settings updated successfully'
                })
            else:
                return jsonify({'error': 'Failed to update inventory settings'}), 500
        
    except Exception as e:
        logger.error(f"Error handling inventory settings: {e}")
        return jsonify({'error': 'Internal server error'}), 500
