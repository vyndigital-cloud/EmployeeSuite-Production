"""
Ultra-Fast Extensions - Minimal initialization overhead
"""
from flask_sqlalchemy import SQLAlchemy

# Configure SQLAlchemy for maximum speed
class FastSQLAlchemy(SQLAlchemy):
    def __init__(self, *args, **kwargs):
        # Speed optimizations
        kwargs.setdefault('engine_options', {
            'pool_size': 5,
            'max_overflow': 10,
            'pool_pre_ping': True,
            'pool_recycle': 1800,
            'echo': False,  # Disable SQL logging
            'future': True,  # Use SQLAlchemy 2.0 style
        })
        super().__init__(*args, **kwargs)

# Single global instance
db = FastSQLAlchemy()

# Fast initialization function
def init_extensions(app):
    """Ultra-fast extension initialization"""
    db.init_app(app)
    
    # Optimize SQLAlchemy session for speed
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()
