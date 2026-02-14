web: python verify_static_assets.py && gunicorn --worker-class=sync --workers=2 --timeout=600 --max-requests=1000 --max-requests-jitter=100 main:app
