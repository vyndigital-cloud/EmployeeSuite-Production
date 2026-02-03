"""
Simple App Factory
"""
import logging
import os
from flask import Flask

def create_app():
    """Create simple Flask app"""
    app = Flask(__name__)
    app.static_folder = 'static'
    app.static_url_path = '/static'
    
    # Basic config
    app.config.update({
        'SECRET_KEY': os.getenv('SECRET_KEY', 'dev-secret-key'),
        'SQLALCHEMY_DATABASE_URI': os.getenv('DATABASE_URL', 'sqlite:///app.db'),
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })
    
    # Initialize database
    from models import db
    db.init_app(app)
    
    # Initialize login manager
    from flask_login import LoginManager
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from core_routes import core_bp
    from auth import auth_bp
    from shopify_oauth import oauth_bp
    from shopify_routes import shopify_bp
    from billing import billing_bp
    from features_pages import features_pages_bp
    from legal_routes import legal_bp
    from gdpr_compliance import gdpr_bp
    from webhook_shopify import webhook_shopify_bp
    
    app.register_blueprint(core_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(oauth_bp)
    app.register_blueprint(shopify_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(features_pages_bp)
    app.register_blueprint(legal_bp)
    app.register_blueprint(gdpr_bp)
    app.register_blueprint(webhook_shopify_bp)
    
    return app

def create_fortress_app():
    """Alias for compatibility"""
    return create_app()
