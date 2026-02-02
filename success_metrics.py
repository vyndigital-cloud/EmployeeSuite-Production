"""
Success Metrics Tracking
Track key business metrics for growth
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

logger = logging.getLogger(__name__)


def track_conversion_metrics() -> Dict[str, Any]:
    """Track key conversion metrics"""
    try:
        from models import User, db

        # Calculate key metrics
        total_users = User.query.count()

        # Trial to paid conversion
        trial_users = User.query.filter(
            User.trial_ends_at > datetime.utcnow(), User.is_subscribed == False
        ).count()

        paid_users = User.query.filter(User.is_subscribed == True).count()

        # Monthly recurring revenue (MRR)
        mrr = paid_users * 39  # $39/month per user

        # Annual recurring revenue (ARR)
        arr = mrr * 12

        return {
            "total_users": total_users,
            "trial_users": trial_users,
            "paid_users": paid_users,
            "conversion_rate": (paid_users / total_users * 100)
            if total_users > 0
            else 0,
            "mrr": mrr,
            "arr": arr,
            "last_updated": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Metrics tracking failed: {e}")
        return {"error": str(e)}


def get_growth_projection(current_users: int) -> Dict[str, Any]:
    """Project growth to 1K and 10K users"""

    # Conservative growth assumptions
    monthly_growth_rate = 0.20  # 20% month-over-month growth

    months_to_1k = 0
    months_to_10k = 0

    users = current_users
    month = 0

    while users < 10000:
        month += 1
        users = int(users * (1 + monthly_growth_rate))

        if users >= 1000 and months_to_1k == 0:
            months_to_1k = month

        if users >= 10000 and months_to_10k == 0:
            months_to_10k = month
            break

    return {
        "current_users": current_users,
        "months_to_1k_users": months_to_1k,
        "months_to_10k_users": months_to_10k,
        "projected_1k_mrr": 1000 * 39,  # $39K MRR at 1K users
        "projected_10k_mrr": 10000 * 39,  # $390K MRR at 10K users
        "projected_1k_arr": 1000 * 39 * 12,  # $468K ARR at 1K users
        "projected_10k_arr": 10000 * 39 * 12,  # $4.68M ARR at 10K users
    }
