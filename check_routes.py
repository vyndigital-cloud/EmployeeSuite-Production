"""
Diagnostic script to check all routes and configurations
Run this to see what's working and what's not
"""
from app_factory import create_app

def check_routes():
    """Check all registered routes"""
    app = create_app()
    
    print("\n" + "="*60)
    print("REGISTERED ROUTES")
    print("="*60)
    
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': ','.join(rule.methods - {'HEAD', 'OPTIONS'}),
            'path': str(rule)
        })
    
    # Sort by path
    routes.sort(key=lambda x: x['path'])
    
    # Print routes
    for route in routes:
        print(f"{route['methods']:12} {route['path']:40} -> {route['endpoint']}")
    
    print(f"\nTotal routes: {len(routes)}")
    
    # Check critical routes
    print("\n" + "="*60)
    print("CRITICAL ROUTES CHECK")
    print("="*60)
    
    critical_routes = [
        '/install',
        '/auth/callback',
        '/settings/shopify',
        '/settings/shopify/connect',
        '/settings/shopify/disconnect',
        '/ping',
        '/test-embed',
        '/',
    ]
    
    for path in critical_routes:
        found = any(str(rule) == path for rule in app.url_map.iter_rules())
        status = "✅" if found else "❌"
        print(f"{status} {path}")
    
    # Check blueprints
    print("\n" + "="*60)
    print("REGISTERED BLUEPRINTS")
    print("="*60)
    
    for name, blueprint in app.blueprints.items():
        print(f"✅ {name}")
    
    print(f"\nTotal blueprints: {len(app.blueprints)}")

if __name__ == "__main__":
    check_routes()
