from datetime import datetime, timedelta

from email_service import send_trial_expiry_warning
from logging_config import logger
from models import User, db


def send_trial_warnings():
    """Run daily - send warning emails to users 1 day before trial expires"""
    # FIXED: Import app factory instead of app directly
    from app_factory import create_app

    app = create_app()
    with app.app_context():
        tomorrow = datetime.utcnow() + timedelta(days=1)
        day_after = datetime.utcnow() + timedelta(days=2)

        # Find users whose trial expires tomorrow
        users = User.query.filter(
            User.is_subscribed == False,
            User.trial_ends_at >= tomorrow,
            User.trial_ends_at < day_after,
        ).all()

        for user in users:
            try:
                days_left = (user.trial_ends_at - datetime.utcnow()).days
                send_trial_expiry_warning(user.email, days_left)
                logger.info(f"Sent trial warning email to {user.email}")
            except Exception as e:
                logger.error(f"Failed to send trial warning to {user.email}: {e}")

        logger.info(f"Sent {len(users)} trial warning emails")


if __name__ == "__main__":
    send_trial_warnings()
