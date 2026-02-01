"""
Enterprise Monitoring & Observability
Implements comprehensive monitoring for 100k+ users
"""

import logging
import os
import time
from datetime import datetime
from functools import wraps

import psutil
from flask import g, request

logger = logging.getLogger(__name__)


class EnterpriseMonitoring:
    def __init__(self):
        self.metrics = {}
        self.alerts = []

    def track_request(self, endpoint, duration, status_code, user_id=None):
        """Track request metrics"""
        metric_key = f"requests:{endpoint}"

        if metric_key not in self.metrics:
            self.metrics[metric_key] = {
                "count": 0,
                "total_duration": 0,
                "error_count": 0,
                "last_request": None,
            }

        self.metrics[metric_key]["count"] += 1
        self.metrics[metric_key]["total_duration"] += duration
        self.metrics[metric_key]["last_request"] = datetime.utcnow().isoformat()

        if status_code >= 400:
            self.metrics[metric_key]["error_count"] += 1

        # Check for performance issues
        avg_duration = (
            self.metrics[metric_key]["total_duration"]
            / self.metrics[metric_key]["count"]
        )
        if avg_duration > 5.0:  # 5 second threshold
            self.create_alert(
                "SLOW_ENDPOINT",
                {
                    "endpoint": endpoint,
                    "avg_duration": avg_duration,
                    "request_count": self.metrics[metric_key]["count"],
                },
            )

    def track_business_metric(self, metric_name, value, user_id=None):
        """Track business metrics"""
        business_key = f"business:{metric_name}"

        if business_key not in self.metrics:
            self.metrics[business_key] = {"total": 0, "count": 0, "last_updated": None}

        self.metrics[business_key]["total"] += value
        self.metrics[business_key]["count"] += 1
        self.metrics[business_key]["last_updated"] = datetime.utcnow().isoformat()

    def get_system_metrics(self):
        """Get system performance metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {}

    def create_alert(self, alert_type, details):
        """Create monitoring alert"""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": alert_type,
            "details": details,
            "severity": self.get_alert_severity(alert_type),
        }

        self.alerts.append(alert)
        logger.warning(f"ALERT: {alert}")

        # In production, send to alerting system (PagerDuty, Slack, etc.)
        # self.send_alert(alert)

    def get_alert_severity(self, alert_type):
        """Determine alert severity"""
        high_severity = ["DATABASE_ERROR", "MEMORY_HIGH", "SLOW_ENDPOINT"]
        return "HIGH" if alert_type in high_severity else "MEDIUM"


monitoring = EnterpriseMonitoring()


def monitor_performance(f):
    """Performance monitoring decorator"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()

        try:
            result = f(*args, **kwargs)
            status_code = 200
            return result
        except Exception as e:
            status_code = 500
            raise
        finally:
            duration = time.time() - start_time
            user_id = getattr(g, "current_user_id", None)

            monitoring.track_request(
                request.endpoint or "unknown", duration, status_code, user_id
            )

    return decorated_function
