# order_processing.py
import json
import os

def process_orders(creds_path='creds.json'):
    """
    Process orders from creds.json or dummy data
    Returns: Success message string
    """
    try:
        # Check if creds file exists
        if os.path.exists(creds_path):
            with open(creds_path, 'r') as f:
                creds = json.load(f)
            message = "Orders processed successfully ✅"
            print(message)
            return message
        else:
            # Use dummy data if no creds file
            dummy_orders = [
                {"id": 1, "product": "Widget A", "quantity": 2, "price": 50, "customer": "John"},
                {"id": 2, "product": "Widget B", "quantity": 1, "price": 75, "customer": "Jane"}
            ]
            message = f"Processed {len(dummy_orders)} dummy orders ✅"
            print(message)
            return message
            
    except FileNotFoundError:
        error_msg = f"Error: {creds_path} not found!"
        print(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error processing orders: {e}"
        print(error_msg)
        return error_msg


if __name__ == "__main__":
    # Test the function
    result = process_orders()
    print(f"Result: {result}")
