# reporting.py - Temporary version without pandas

def generate_report():
    """
    Generate profit report (simplified version)
    Returns: dict with dummy data
    """
    return {
        "message": "Report generated (pandas disabled for local testing)",
        "note": "Full reports will work on Render with Python 3.11"
    }

if __name__ == "__main__":
    report = generate_report()
    print(report)
