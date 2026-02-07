"""
Smoke tests - Critical tests that must pass before deployment.
These tests prevent production outages by catching basic errors.
"""
import pytest
from flask import session


@pytest.fixture
def app():
    """Create application for testing"""
    from app_factory import create_app
    from config import config
    
    app = create_app(config['testing'])
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    app.config['WTF_CSRF_ENABLED'] = False
    
    yield app


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def db(app):
    """Create test database"""
    from models import db as _db
    
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


# CRITICAL: These tests must pass or deployment fails
class TestSmokeTests:
    """Critical smoke tests for deployment validation"""
    
    def test_home_route_returns_200(self, client):
        """Test that home route is accessible"""
        response = client.get('/')
        # Should either return 200 (logged in) or 302 (redirect to login)
        assert response.status_code in [200, 302], \
            f"Home route returned {response.status_code}, expected 200 or 302"
    
    def test_auth_callback_no_500(self, client):
        """Test that /auth/callback doesn't crash with 500 error"""
        # Test with minimal parameters (should handle gracefully)
        response = client.get('/auth/callback')
        # Should NOT return 500 - can be 400 (bad request) or 302 (redirect)
        assert response.status_code != 500, \
            f"/auth/callback returned 500 error - DEPLOYMENT BLOCKED"
    
    def test_auth_callback_with_shop_param(self, client):
        """Test /auth/callback with shop parameter doesn't crash"""
        response = client.get('/auth/callback?shop=test.myshopify.com')
        # Should handle shop parameter without crashing
        assert response.status_code != 500, \
            f"/auth/callback with shop param returned 500 - DEPLOYMENT BLOCKED"


class TestLoadUserFromRequest:
    """Test the load_user_from_request function that caused production issues"""
    
    def test_load_user_from_request_with_session(self, app, db):
        """Test that session is preserved when user is authenticated"""
        from models import User
        from flask import session as flask_session
        
        with app.test_request_context():
            # Create a test user
            user = User(email='test@example.com', password_hash='dummy')
            db.session.add(user)
            db.session.commit()
            
            # Simulate authenticated session
            flask_session['_user_id'] = user.id
            
            # Mock request with shop parameters
            from flask import request
            with app.test_request_context('/?shop=test.myshopify.com&hmac=abc123'):
                from app_factory import login_manager
                result = login_manager._request_callback(request)
                
                # Should return the session user, NOT try to auto-login from shop params
                assert result is not None, "load_user_from_request should return user from session"
                assert result.id == user.id, "Should preserve session user"
    
    def test_load_user_from_request_with_shop(self, app, db):
        """Test that ShopifyStore query works (not User.shop_url)"""
        from models import User, ShopifyStore
        
        with app.test_request_context():
            # Create user and store
            user = User(email='shop@example.com', password_hash='dummy')
            db.session.add(user)
            db.session.commit()
            
            store = ShopifyStore(
                user_id=user.id,
                shop_url='test.myshopify.com',
                access_token='dummy_token'
            )
            db.session.add(store)
            db.session.commit()
            
            # Test with shop parameter and no session
            with app.test_request_context('/?shop=test.myshopify.com&hmac=abc123'):
                from flask import request
                from app_factory import login_manager
                
                # This should NOT crash with "User has no attribute shop_url"
                try:
                    result = login_manager._request_callback(request)
                    # If it works, should return user
                    assert result is None or isinstance(result, User), \
                        "Should return User instance or None"
                except AttributeError as e:
                    if 'shop_url' in str(e):
                        pytest.fail(f"CRITICAL: Still querying User.shop_url instead of ShopifyStore: {e}")
                    raise


class TestModelRelationships:
    """Test database model relationships"""
    
    def test_user_shopify_store_relationship(self, app, db):
        """Verify User <-> ShopifyStore relationship works"""
        from models import User, ShopifyStore
        
        with app.app_context():
            user = User(email='relationship@example.com', password_hash='dummy')
            db.session.add(user)
            db.session.commit()
            
            store = ShopifyStore(
                user_id=user.id,
                shop_url='relationship.myshopify.com',
                access_token='test_token'
            )
            db.session.add(store)
            db.session.commit()
            
            # Test relationship
            assert store.user.id == user.id, "ShopifyStore.user relationship failed"
            assert user.shopify_stores.count() > 0, "User.shopify_stores relationship failed"
