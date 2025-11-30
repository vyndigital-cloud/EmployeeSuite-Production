# reporting.py - Temporary simple version

def generate_report():
    """Generate basic report preview"""
    return {
        "products": [
            {"name": "Product A", "stock": 10, "revenue": "$500"},
            {"name": "Product B", "stock": 5, "revenue": "$375"},
            {"name": "Product C", "stock": 15, "revenue": "$750"}
        ],
        "total_revenue": "$1,625",
        "total_products": 3
    }

if __name__ == "__main__":
    print(generate_report())
