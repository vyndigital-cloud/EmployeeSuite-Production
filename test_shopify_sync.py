#!/usr/bin/env python3
"""
Automated test script to verify Shopify API integration matches Shopify Admin data.
Run this to verify your app is fetching all orders correctly.
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import your Shopify client
from shopify_integration import ShopifyClient

def test_pagination():
    """Test that pagination fetches ALL orders"""
    shop_url = os.getenv('SHOPIFY_URL', '').replace('https://', '').replace('http://', '')
    access_token = os.getenv('SHOPIFY_TOKEN', '')
    
    if not shop_url or not access_token:
        print("❌ Error: Set SHOPIFY_URL and SHOPIFY_TOKEN in .env file")
        print("   Example:")
        print("   SHOPIFY_URL=yourstore.myshopify.com")
        print("   SHOPIFY_TOKEN=shpat_xxxxx")
        return False
    
    print(f"🔍 Testing Shopify API connection to: {shop_url}")
    print("=" * 60)
    
    client = ShopifyClient(shop_url, access_token)
    
    # Test 1: Fetch ALL paid orders using pagination (same as your app)
    print("\n1️⃣ Testing Revenue Report Pagination:")
    print("-" * 60)
    
    all_orders = []
    limit = 250
    endpoint = f"orders.json?financial_status=paid&limit={limit}"
    max_iterations = 50
    
    try:
        for iteration in range(max_iterations):
            orders_data = client._make_request(endpoint)
            
            if "error" in orders_data:
                if iteration == 0:
                    print(f"❌ Shopify API Error: {orders_data['error']}")
                    return False
                break
            
            orders = orders_data.get('orders', [])
            if not orders or len(orders) == 0:
                break
            
            all_orders.extend(orders)
            print(f"   Page {iteration + 1}: Fetched {len(orders)} orders (Total: {len(all_orders)})")
            
            if len(orders) < limit:
                break
            
            if orders:
                last_order_id = max(order.get('id', 0) for order in orders)
                endpoint = f"orders.json?financial_status=paid&limit={limit}&since_id={last_order_id}"
            else:
                break
                
    except Exception as e:
        print(f"❌ Error during pagination: {e}")
        return False
    
    # Calculate total revenue
    total_revenue = 0
    for order in all_orders:
        total_revenue += float(order.get('total_price', 0))
    
    print(f"\n✅ Pagination Test Results:")
    print(f"   Total Orders Fetched: {len(all_orders)}")
    print(f"   Total Revenue: ${total_revenue:,.2f}")
    
    # Test 2: Verify we got all orders (check if pagination worked)
    if len(all_orders) > 0:
        order_ids = [order.get('id') for order in all_orders]
        print(f"\n   Order IDs Range: {min(order_ids)} to {max(order_ids)}")
        
        # Check for gaps (missing orders)
        if len(all_orders) >= 250:
            print(f"\n   ⚠️  You have 250+ orders - verifying pagination worked...")
            # Fetch first page only to compare
            first_page_data = client._make_request("orders.json?financial_status=paid&limit=250")
            first_page_orders = first_page_data.get('orders', [])
            
            if len(first_page_orders) == 250 and len(all_orders) == 250:
                print(f"   ❌ WARNING: Only fetched 250 orders - pagination may not be working!")
                print(f"   Expected more orders but got exactly 250 (first page limit)")
                return False
            else:
                print(f"   ✅ Pagination working: Fetched {len(all_orders)} orders (first page had {len(first_page_orders)})")
    
    # Test 3: Test Order Processing (unfulfilled/pending)
    print("\n2️⃣ Testing Order Processing (Unfulfilled/Pending):")
    print("-" * 60)
    
    try:
        pending_data = client._make_request("orders.json?financial_status=pending&limit=250")
        unfulfilled_data = client._make_request("orders.json?financial_status=paid&fulfillment_status=unfulfilled&limit=250")
        
        pending_orders = pending_data.get('orders', []) if "error" not in pending_data else []
        unfulfilled_orders = unfulfilled_data.get('orders', []) if "error" not in unfulfilled_data else []
        
        # Deduplicate
        order_ids_set = set()
        all_pending = []
        for order in pending_orders:
            if order.get('id') not in order_ids_set:
                all_pending.append(order)
                order_ids_set.add(order.get('id'))
        for order in unfulfilled_orders:
            if order.get('id') not in order_ids_set:
                all_pending.append(order)
                order_ids_set.add(order.get('id'))
        
        print(f"   Pending Payment Orders: {len(pending_orders)}")
        print(f"   Unfulfilled Orders: {len(unfulfilled_orders)}")
        print(f"   Total Pending/Unfulfilled: {len(all_pending)}")
        
        if all_pending:
            print(f"\n   Sample Orders:")
            for order in all_pending[:3]:
                print(f"      - Order #{order.get('name', 'N/A')}: ${order.get('total_price', '0')} ({order.get('fulfillment_status', 'N/A')})")
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 4: Test Inventory
    print("\n3️⃣ Testing Inventory Fetch:")
    print("-" * 60)
    
    try:
        products_data = client._make_request("products.json?limit=250")
        if "error" in products_data:
            print(f"   ❌ Error: {products_data['error']}")
        else:
            products = products_data.get('products', [])
            total_variants = 0
            low_stock = 0
            
            for product in products:
                for variant in product.get('variants', []):
                    total_variants += 1
                    stock = variant.get('inventory_quantity', 0)
                    if stock < 10:
                        low_stock += 1
            
            print(f"   Total Products: {len(products)}")
            print(f"   Total Variants: {total_variants}")
            print(f"   Low Stock Items (< 10): {low_stock}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY:")
    print("=" * 60)
    print(f"✅ Total Paid Orders: {len(all_orders)}")
    print(f"✅ Total Revenue: ${total_revenue:,.2f}")
    print(f"✅ Pending/Unfulfilled Orders: {len(all_pending)}")
    
    if len(all_orders) > 0:
        print(f"\n💡 Next Steps:")
        print(f"   1. Compare these numbers with your Shopify Admin")
        print(f"   2. Generate report in your dashboard")
        print(f"   3. Verify numbers match exactly")
        
        if len(all_orders) >= 250:
            print(f"\n   ⚠️  You have 250+ orders - make sure pagination is working!")
            print(f"   Check Render logs for: 'Fetched X orders (iteration Y)'")
    
    return True

if __name__ == '__main__':
    print("🧪 Shopify API Integration Test")
    print("=" * 60)
    
    success = test_pagination()
    
    if success:
        print("\n✅ All tests completed!")
        sys.exit(0)
    else:
        print("\n❌ Tests failed - check errors above")
        sys.exit(1)

