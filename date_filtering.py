"""
Date Filtering Utilities for Reports
Handles date range selection and filtering
"""
from datetime import datetime, timedelta
from flask import request

def parse_date_range():
    """Parse date range from request parameters"""
    # Get date range from query params
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    days = request.args.get('days', type=int)
    
    # Default to last 30 days if nothing specified
    if not start_date_str and not end_date_str and not days:
        days = 30
    
    if days:
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
    elif start_date_str and end_date_str:
        try:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except ValueError:
            # Fallback to last 30 days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
    else:
        # Default to last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
    
    return start_date, end_date

def filter_orders_by_date(orders, start_date, end_date):
    """Filter orders by date range"""
    filtered = []
    for order in orders:
        created_at_str = order.get('created_at', '')
        if not created_at_str:
            continue
        
        try:
            # Parse Shopify date format: "2024-01-15T10:30:00-05:00"
            order_date = datetime.fromisoformat(created_at_str.replace('Z', '+00:00'))
            # Convert to UTC if needed
            if order_date.tzinfo:
                order_date = order_date.astimezone(datetime.utcnow().tzinfo).replace(tzinfo=None)
            
            if start_date <= order_date <= end_date:
                filtered.append(order)
        except (ValueError, AttributeError):
            # If date parsing fails, include the order (better to show than hide)
            filtered.append(order)
    
    return filtered

def filter_products_by_date(products, start_date, end_date):
    """Filter products by date (if they have created_at)"""
    # Products don't typically have date filters, but we can filter variants
    # For now, return all products
    return products

def get_date_range_options():
    """Get predefined date range options"""
    return [
        {'label': 'Last 7 days', 'days': 7},
        {'label': 'Last 30 days', 'days': 30},
        {'label': 'Last 90 days', 'days': 90},
        {'label': 'Last 6 months', 'days': 180},
        {'label': 'Last year', 'days': 365},
        {'label': 'All time', 'days': None},
        {'label': 'Custom range', 'days': 'custom'},
    ]

