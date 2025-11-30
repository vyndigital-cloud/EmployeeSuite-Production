# inventory.py
import json

def update_inventory():
    """
    Track inventory and alert for low stock
    Returns: Status message string
    """
    try:
        # Dummy inventory data
        inventory = {
            "Widget A": {"stock": 10, "threshold": 5},
            "Widget B": {"stock": 1, "threshold": 5},
            "Widget C": {"stock": 20, "threshold": 5}
        }
        
        messages = []
        low_stock_items = []
        
        for product, data in inventory.items():
            if data["stock"] < data["threshold"]:
                alert = f"Low stock alert 🚨: {product} - {data['stock']} units left"
                print(alert)
                low_stock_items.append(product)
                messages.append(alert)
        
        if low_stock_items:
            result = "\n".join(messages)
        else:
            result = "All inventory levels are healthy ✅"
            print(result)
        
        return result
        
    except Exception as e:
        error_msg = f"Error updating inventory: {e}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    # Test the function
    result = update_inventory()
    print(f"Result: {result}")
