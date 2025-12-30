#!/usr/bin/env python3
"""
Scheduled Reports Worker
Runs as a cron job to send scheduled reports via email/SMS
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import app
from enhanced_models import ScheduledReport, db
from enhanced_features import send_scheduled_report
from logging_config import logger

def run_scheduled_reports():
    """Run scheduled reports - call this from cron job"""
    with app.app_context():
        try:
            now = datetime.utcnow()
            logger.info(f"Running scheduled reports worker at {now}")
            
            # Find reports due to be sent
            due_reports = ScheduledReport.query.filter(
                ScheduledReport.is_active == True,
                ScheduledReport.next_send_at <= now
            ).all()
            
            logger.info(f"Found {len(due_reports)} reports due to be sent")
            
            for report in due_reports:
                try:
                    logger.info(f"Processing scheduled report {report.id} for user {report.user_id}")
                    
                    # Send the report
                    send_scheduled_report(report)
                    
                    # Update report status
                    report.last_sent_at = now
                    report.next_send_at = report.calculate_next_send()
                    db.session.commit()
                    
                    logger.info(f"Successfully sent report {report.id}, next send at {report.next_send_at}")
                except Exception as e:
                    logger.error(f"Error sending report {report.id}: {str(e)}", exc_info=True)
                    db.session.rollback()
                    # Continue with next report even if this one fails
            
            logger.info("Scheduled reports worker completed")
        except Exception as e:
            logger.error(f"Error in scheduled reports worker: {str(e)}", exc_info=True)

if __name__ == '__main__':
    run_scheduled_reports()

