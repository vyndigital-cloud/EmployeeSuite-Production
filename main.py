# main.py
import os
import sys
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report


def get_creds_path(filename="creds.json"):
    """
    Get the path for creds.json in both dev and PyInstaller environments
    """
    if getattr(sys, 'frozen', False):
        # Running as PyInstaller exe
        base_path = sys._MEIPASS
    else:
        # Running as normal script
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, filename)


def run_suite():
    """
    Main function to run the entire Employee Suite automation
    """
    print("="*60)
    print("Starting 1 Employee Suite Automation ✅")
    print("="*60)
    
    # Get creds path
    creds_path = get_creds_path()
    
    # Step 1: Process Orders
    print("\nStep 1: Processing Orders...")
    try:
        order_result = process_orders(creds_path=creds_path)
        print(f"✅ {order_result}")
    except Exception as e:
        print(f"❌ Error in order processing: {e}")
    
    # Step 2: Update Inventory
    print("\nStep 2: Updating Inventory...")
    try:
        inventory_result = update_inventory()
        print(f"✅ {inventory_result}")
    except Exception as e:
        print(f"❌ Error in inventory update: {e}")
    
    # Step 3: Generate Report
    print("\nStep 3: Generating Profit Report...")
    try:
        report_df = generate_report()
        if not report_df.empty:
            print(f"✅ Report generated with {len(report_df)} items")
            print(f"\nTotal Profit: ${report_df['profit'].sum():.2f}")
        else:
            print("❌ Report is empty")
    except Exception as e:
        print(f"❌ Error in report generation: {e}")
    
    print("\n" + "="*60)
    print("Suite execution complete!")
    print("="*60)


if __name__ == "__main__":
    run_suite()
