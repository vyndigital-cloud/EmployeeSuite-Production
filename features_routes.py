"""
Feature routes for new functionality
"""

from flask import Blueprint, render_template_string, request

features_bp = Blueprint("features", __name__)


@features_bp.route("/features/welcome")
def welcome():
    return render_template_string("""
    <h1>Welcome to Employee Suite Features</h1>
    <p>Feature pages coming soon.</p>
    <a href="/dashboard">Back to Dashboard</a>
    """)


@features_bp.route("/features/csv-exports")
def csv_exports():
    return render_template_string("""
    <h1>CSV Exports</h1>
    <p>CSV export functionality coming soon.</p>
    <a href="/dashboard">Back to Dashboard</a>
    """)


@features_bp.route("/features/scheduled-reports")
def scheduled_reports():
    return render_template_string("""
    <h1>Scheduled Reports</h1>
    <p>Scheduled reports functionality coming soon.</p>
    <a href="/dashboard">Back to Dashboard</a>
    """)


@features_bp.route("/features/dashboard")
def comprehensive_dashboard():
    return render_template_string("""
    <h1>Comprehensive Dashboard</h1>
    <p>Full dashboard functionality coming soon.</p>
    <a href="/dashboard">Back to Dashboard</a>
    """)
