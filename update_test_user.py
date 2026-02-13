from app_factory import create_app
from models import db, User

app = create_app()

with app.app_context():
    # Find the test user created by the browser subagent
    user = User.query.filter_by(email='a@b.com').first()
    if user:
        print(f"Found user: {user.email} (ID: {user.id})")
        print(f"Current status - Subscribed: {user.is_subscribed}, Trial Active: {user.is_trial_active()}")
        
        # Manually validat subscription
        user.is_subscribed = True
        db.session.commit()
        
        print(f"✅ Updated user {user.email} to is_subscribed=True")
    else:
        print("❌ User a@b.com not found")
