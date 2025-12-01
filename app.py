from flask import Flask, jsonify, render_template_string, redirect, url_for
from flask_login import LoginManager, login_required, current_user
from flask_bcrypt import Bcrypt
import os
from datetime import datetime

from models import db, User, ShopifyStore
from auth import auth_bp, bcrypt as auth_bcrypt
from shopify_routes import shopify_bp
from billing import billing_bp
from admin_routes import admin_bp
from legal_routes import legal_bp
from order_processing import process_orders
from inventory import update_inventory
from reporting import generate_report

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///employeesuite.db')
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)
app.register_blueprint(shopify_bp)
app.register_blueprint(billing_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(legal_bp)

DASHBOARD_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Dashboard - Employee Suite</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #6366f1;
            --primary-dark: #4f46e5;
            --primary-light: #818cf8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
            --dark: #0f172a;
            --gray-50: #f8fafc;
            --gray-100: #f1f5f9;
            --gray-200: #e2e8f0;
            --gray-300: #cbd5e1;
            --gray-400: #94a3b8;
            --gray-500: #64748b;
            --gray-600: #475569;
            --gray-700: #334155;
            --gray-800: #1e293b;
            --gray-900: #0f172a;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }
        
        /* Animated Background */
        .bg-decoration {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            z-index: 0;
            pointer-events: none;
        }
        .bg-blob {
            position: absolute;
            border-radius: 50%;
            filter: blur(80px);
            opacity: 0.3;
            animation: float 20s ease-in-out infinite;
        }
        .blob-1 {
            width: 500px;
            height: 500px;
            background: linear-gradient(45deg, #667eea, #764ba2);
            top: -250px;
            left: -250px;
            animation-delay: 0s;
        }
        .blob-2 {
            width: 400px;
            height: 400px;
            background: linear-gradient(45deg, #f093fb, #f5576c);
            bottom: -200px;
            right: -200px;
            animation-delay: 7s;
        }
        .blob-3 {
            width: 350px;
            height: 350px;
            background: linear-gradient(45deg, #4facfe, #00f2fe);
            top: 50%;
            right: 10%;
            animation-delay: 14s;
        }
        @keyframes float {
            0%, 100% { transform: translate(0, 0) rotate(0deg); }
            33% { transform: translate(30px, -50px) rotate(120deg); }
            66% { transform: translate(-20px, 20px) rotate(240deg); }
        }
        
        /* Header */
        .header {
            position: relative;
            z-index: 10;
            backdrop-filter: blur(20px) saturate(180%);
            background: rgba(255, 255, 255, 0.95);
            border-bottom: 1px solid rgba(255, 255, 255, 0.2);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.05);
        }
        .header-content {
            max-width: 1400px;
            margin: 0 auto;
            padding: 0 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            height: 72px;
        }
        .logo {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 24px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .logo-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
        }
        .header-actions {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .user-badge {
            background: var(--gray-100);
            padding: 8px 16px;
            border-radius: 100px;
            font-size: 14px;
            color: var(--gray-700);
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .user-avatar {
            width: 28px;
            height: 28px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 12px;
            font-weight: 700;
        }
        .btn-header {
            padding: 10px 20px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 600;
            text-decoration: none;
            border: none;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }
        .btn-subscribe {
            background: linear-gradient(135deg, var(--warning) 0%, #f97316 100%);
            color: white;
            box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
        }
        .btn-subscribe:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4);
        }
        .btn-settings {
            background: var(--gray-100);
            color: var(--gray-700);
        }
        .btn-settings:hover {
            background: var(--gray-200);
            transform: translateY(-2px);
        }
        .btn-logout {
            background: transparent;
            color: var(--gray-600);
            border: 1px solid var(--gray-300);
        }
        .btn-logout:hover {
            background: var(--gray-100);
            border-color: var(--gray-400);
        }
        
        /* Container */
        .container {
            position: relative;
            z-index: 5;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 32px 80px;
        }
        
        /* Trial Banner */
        .trial-banner {
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(245, 158, 11, 0.2);
            border-left: 4px solid var(--warning);
            padding: 24px 28px;
            border-radius: 16px;
            margin-bottom: 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
            animation: slideDown 0.5s ease-out;
        }
        @keyframes slideDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .trial-info h3 {
            color: var(--gray-900);
            font-size: 18px;
            font-weight: 700;
            margin-bottom: 6px;
        }
        .trial-info p {
            color: var(--gray-600);
            font-size: 14px;
        }
        .trial-countdown {
            text-align: center;
            padding: 16px 24px;
            background: linear-gradient(135deg, var(--warning) 0%, #f97316 100%);
            border-radius: 12px;
            box-shadow: 0 4px 16px rgba(245, 158, 11, 0.3);
        }
        .days-left {
            font-size: 40px;
            font-weight: 800;
            color: white;
            line-height: 1;
        }
        .days-label {
            font-size: 12px;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-top: 4px;
        }
        
        /* Setup Banner */
        .setup-banner {
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            padding: 32px;
            border-radius: 20px;
            margin-bottom: 32px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.5);
            position: relative;
            overflow: hidden;
            animation: slideDown 0.5s ease-out;
        }
        .setup-banner::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary), var(--primary-light), var(--primary));
            background-size: 200% 100%;
            animation: shimmer 3s linear infinite;
        }
        @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
        }
        .setup-content {
            display: flex;
            align-items: center;
            gap: 24px;
        }
        .setup-icon {
            width: 80px;
            height: 80px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            flex-shrink: 0;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
        }
        .setup-text h3 {
            font-size: 24px;
            font-weight: 800;
            color: var(--gray-900);
            margin-bottom: 8px;
        }
        .setup-text p {
            font-size: 15px;
            color: var(--gray-600);
            line-height: 1.6;
            margin-bottom: 16px;
        }
        .btn-setup {
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            padding: 12px 24px;
            border-radius: 10px;
            font-weight: 700;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
            gap: 8px;
            font-size: 15px;
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        .btn-setup:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4);
        }
        
        /* Stats Grid */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 48px;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            padding: 28px;
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
        }
        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--primary-light));
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-8px);
            box-shadow: 0 16px 48px rgba(0, 0, 0, 0.12);
        }
        .stat-card:hover::before {
            transform: scaleX(1);
        }
        .stat-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }
        .stat-icon {
            width: 56px;
            height: 56px;
            background: linear-gradient(135deg, var(--gray-100) 0%, var(--gray-200) 100%);
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
        }
        .stat-label {
            font-size: 13px;
            color: var(--gray-500);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 36px;
            font-weight: 800;
            background: linear-gradient(135deg, var(--gray-900) 0%, var(--gray-700) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            line-height: 1.2;
        }
        
        /* Actions Section */
        .actions-header {
            margin-bottom: 24px;
        }
        .actions-header h2 {
            font-size: 28px;
            font-weight: 800;
            color: white;
            text-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            margin-bottom: 8px;
        }
        .actions-header p {
            font-size: 16px;
            color: rgba(255, 255, 255, 0.8);
        }
        .actions-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
            gap: 24px;
            margin-bottom: 48px;
        }
        .action-card {
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            overflow: hidden;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
            position: relative;
        }
        .action-card::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.1) 0%, transparent 70%);
            transform: scale(0);
            transition: transform 0.6s ease;
        }
        .action-card:hover::before {
            transform: scale(1);
        }
        .action-card:hover {
            transform: translateY(-12px) scale(1.02);
            box-shadow: 0 24px 64px rgba(0, 0, 0, 0.16);
            border-color: rgba(99, 102, 241, 0.3);
        }
        .action-header-section {
            padding: 32px;
            background: linear-gradient(135deg, var(--gray-50) 0%, white 100%);
            position: relative;
            z-index: 1;
        }
        .action-icon-box {
            width: 72px;
            height: 72px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 36px;
            margin-bottom: 20px;
            box-shadow: 0 8px 24px rgba(99, 102, 241, 0.3);
            transition: all 0.3s ease;
        }
        .action-card:hover .action-icon-box {
            transform: scale(1.1) rotate(5deg);
            box-shadow: 0 12px 32px rgba(99, 102, 241, 0.4);
        }
        .action-title {
            font-size: 22px;
            font-weight: 800;
            color: var(--gray-900);
            margin-bottom: 8px;
            line-height: 1.3;
        }
        .action-description {
            font-size: 14px;
            color: var(--gray-600);
            line-height: 1.6;
        }
        .action-body {
            padding: 32px;
            position: relative;
            z-index: 1;
        }
        .action-btn {
            width: 100%;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            color: white;
            border: none;
            padding: 16px 28px;
            border-radius: 14px;
            font-size: 16px;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3);
            position: relative;
            overflow: hidden;
        }
        .action-btn::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            width: 0;
            height: 0;
            background: rgba(255, 255, 255, 0.2);
            border-radius: 50%;
            transform: translate(-50%, -50%);
            transition: width 0.6s, height 0.6s;
        }
        .action-btn:hover::before {
            width: 300px;
            height: 300px;
        }
        .action-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 32px rgba(99, 102, 241, 0.5);
        }
        .action-btn:active {
            transform: translateY(0);
        }
        
        /* Output Panel */
        .output-panel {
            background: rgba(255, 255, 255, 0.98);
            backdrop-filter: blur(20px);
            border-radius: 24px;
            border: 1px solid rgba(255, 255, 255, 0.5);
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
            animation: slideUp 0.6s ease-out;
        }
        @keyframes slideUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        .output-header {
            padding: 24px 32px;
            background: linear-gradient(135deg, var(--gray-50) 0%, white 100%);
            border-bottom: 1px solid var(--gray-200);
            font-weight: 700;
            color: var(--gray-900);
            font-size: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .output-icon {
            width: 32px;
            height: 32px;
            background: linear-gradient(135deg, var(--primary) 0%, var(--primary-dark) 100%);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 16px;
        }
        #output {
            padding: 32px;
            min-height: 320px;
            max-height: 600px;
            overflow-y: auto;
            white-space: pre-wrap;
            font-family: 'SF Mono', Monaco, 'Courier New', monospace;
            font-size: 14px;
            line-height: 1.8;
            color: var(--gray-800);
        }
        #output::-webkit-scrollbar {
            width: 8px;
        }
        #output::-webkit-scrollbar-track {
            background: var(--gray-100);
            border-radius: 4px;
        }
        #output::-webkit-scrollbar-thumb {
            background: var(--gray-400);
            border-radius: 4px;
        }
        #output::-webkit-scrollbar-thumb:hover {
            background: var(--gray-500);
        }
        #output:empty:before {
            content: '👆 Click any action above to see results...';
            color: var(--gray-400);
            font-style: italic;
            font-family: 'Inter', sans-serif;
        }
        
        /* Loading State */
        .loading-container {
            text-align: center;
            padding: 80px 20px;
        }
        .loading-spinner {
            display: inline-block;
            width: 50px;
            height: 50px;
            border: 4px solid var(--gray-200);
            border-top: 4px solid var(--primary);
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .loading-text {
            margin-top: 20px;
            color: var(--gray-500);
            font-size: 15px;
            font-weight: 600;
        }
        
        /* Success/Error */
        .success {
            color: var(--success);
            font-weight: 700;
        }
        .error {
            color: var(--danger);
            font-weight: 700;
        }
        
        /* Pulse Animation */
        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.7;
            }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .header-content {
                padding: 0 20px;
                height: 64px;
            }
            .container {
                padding: 24px 20px 60px;
            }
            .logo {
                font-size: 20px;
            }
            .stats-grid {
                grid-template-columns: 1fr;
            }
            .actions-grid {
                grid-template-columns: 1fr;
            }
            .trial-banner {
                flex-direction: column;
                text-align: center;
                gap: 20px;
            }
            .setup-content {
                flex-direction: column;
                text-align: center;
            }
            .user-badge {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="bg-decoration">
        <div class="bg-blob blob-1"></div>
        <div class="bg-blob blob-2"></div>
        <div class="bg-blob blob-3"></div>
    </div>
    
    <div class="header">
        <div class="header-content">
            <div class="logo">
                <div class="logo-icon">🚀</div>
                <span>Employee Suite</span>
            </div>
            <div class="header-actions">
                <div class="user-badge">
                    <div class="user-avatar">{{ current_user.email[0].upper() }}</div>
                    <span>{{ current_user.email }}</span>
                </div>
                <a href="{{ url_for('billing.subscribe') }}" class="btn-header btn-subscribe">
                    💳 Subscribe
                </a>
                <a href="{{ url_for('shopify.shopify_settings') }}" class="btn-header btn-settings">
                    ⚙️ Settings
                </a>
                <a href="{{ url_for('auth.logout') }}" class="btn-header btn-logout">
                    Logout
                </a>
            </div>
        </div>
    </div>
    
    <div class="container">
        {% if trial_active and not is_subscribed %}
        <div class="trial-banner">
            <div class="trial-info">
                <h3>⏰ Free Trial Active</h3>
                <p>Your trial ends in <strong>{{ days_left }} day{{ 's' if days_left != 1 else '' }}</strong>. Subscribe to continue without interruption and unlock full automation.</p>
            </div>
            <div class="trial-countdown">
                <div class="days-left">{{ days_left }}</div>
                <div class="days-label">Days Left</div>
            </div>
        </div>
        {% endif %}
        
        {% if not has_shopify %}
        <div class="setup-banner">
            <div class="setup-content">
                <div class="setup-icon">⚡</div>
                <div class="setup-text">
                    <h3>Quick Setup Required</h3>
                    <p>Connect your Shopify store to unlock real-time inventory tracking, automated alerts, and powerful analytics. Takes less than 2 minutes.</p>
                    <a href="{{ url_for('shopify.shopify_settings') }}" class="btn-setup">
                        Connect Shopify Store
                        <span>→</span>
                    </a>
                </div>
            </div>
        </div>
        {% endif %}
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon">📊</div>
                </div>
                <div class="stat-label">Connection Status</div>
                <div class="stat-value">{{ 'Connected' if has_shopify else 'Setup' }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon">⚡</div>
                </div>
                <div class="stat-label">Automation</div>
                <div class="stat-value">{{ 'Active' if has_shopify else 'Pending' }}</div>
            </div>
            <div class="stat-card">
                <div class="stat-header">
                    <div class="stat-icon">💎</div>
                </div>
                <div class="stat-label">Current Plan</div>
                <div class="stat-value">{{ 'Pro' if is_subscribed else 'Trial' }}</div>
            </div>
        </div>
        
        <div class="actions-header">
            <h2>Automation Dashboard</h2>
            <p>Manage your inventory, orders, and analytics in one powerful platform</p>
        </div>
        
        <div class="actions-grid">
            <div class="action-card">
                <div class="action-header-section">
                    <div class="action-icon-box">📦</div>
                    <div class="action-title">Process Orders</div>
                    <div class="action-description">View and process all pending Shopify orders in real-time with intelligent automation</div>
                </div>
                <div class="action-body">
                    <button class="action-btn" onclick="processOrders()">
                        <span style="position: relative; z-index: 1;">Process Orders Now</span>
                    </button>
                </div>
            </div>
            
            <div class="action-card">
                <div class="action-header-section">
                    <div class="action-icon-box">📊</div>
                    <div class="action-title">Inventory Tracking</div>
                    <div class="action-description">Monitor real-time stock levels across all products with smart low-stock alerts</div>
                </div>
                <div class="action-body">
                    <button class="action-btn" onclick="updateInventory()">
                        <span style="position: relative; z-index: 1;">Check Inventory</span>
                    </button>
                </div>
            </div>
            
            <div class="action-card">
                <div class="action-header-section">
                    <div class="action-icon-box">💰</div>
                    <div class="action-title">Revenue Analytics</div>
                    <div class="action-description">Comprehensive revenue analysis and product performance metrics</div>
                </div>
                <div class="action-body">
                    <button class="action-btn" onclick="generateReport()">
                        <span style="position: relative; z-index: 1;">Generate Report</span>
                    </button>
                </div>
            </div>
        </div>
        
        <div class="output-panel">
            <div class="output-header">
                <div class="output-icon">📋</div>
                <span>Results & Insights</span>
            </div>
            <div id="output"></div>
        </div>
    </div>
    
    <script>
        function showLoading() {
            document.getElementById('output').innerHTML = `
                <div class="loading-container">
                    <div class="loading-spinner"></div>
                    <div class="loading-text">Processing your request...</div>
                </div>
            `;
        }
        
        function processOrders() {
            showLoading();
            fetch('/api/process_orders')
                .then(response => response.json())
                .then(data => {
                    const msg = data.message || data.error;
                    const className = data.success ? 'success' : 'error';
                    const icon = data.success ? '✅' : '❌';
                    document.getElementById('output').innerHTML = `
                        <div style="animation: slideUp 0.3s ease-out;">
                            <h3 class="${className}" style="font-size: 20px; margin-bottom: 16px;">${icon} ${data.success ? 'Orders Processed Successfully' : 'Processing Error'}</h3>
                            <p style="font-size: 15px; line-height: 1.8; color: var(--gray-700);">${msg}</p>
                        </div>
                    `;
                })
                .catch(error => {
                    document.getElementById('output').innerHTML = `
                        <div style="animation: slideUp 0.3s ease-out;">
                            <h3 class="error" style="font-size: 20px; margin-bottom: 16px;">❌ Connection Error</h3>
                            <p style="font-size: 15px; color: var(--gray-700);">${error}</p>
                        </div>
                    `;
                });
        }
        
        function updateInventory() {
            showLoading();
            fetch('/api/update_inventory')
                .then(response => response.json())
                .then(data => {
                    const msg = data.message || data.error;
                    const className = data.success ? 'success' : 'error';
                    const icon = data.success ? '✅' : '❌';
                    document.getElementById('output').innerHTML = `
                        <div style="animation: slideUp 0.3s ease-out;">
                            <h3 class="${className}" style="font-size: 20px; margin-bottom: 16px;">${icon} ${data.success ? 'Inventory Check Complete' : 'Inventory Error'}</h3>
                            <p style="font-size: 15px; line-height: 1.8; white-space: pre-wrap; color: var(--gray-700);">${msg}</p>
                        </div>
                    `;
                })
                .catch(error => {
                    document.getElementById('output').innerHTML = `
                        <div style="animation: slideUp 0.3s ease-out;">
                            <h3 class="error" style="font-size: 20px; margin-bottom: 16px;">❌ Connection Error</h3>
                            <p style="font-size: 15px; color: var(--gray-700);">${error}</p>
                        </div>
                    `;
                });
        }
        
        function generateReport() {
            showLoading();
            fetch('/api/generate_report')
                .then(response => response.text())
                .then(html => {
                    document.getElementById('output').innerHTML = `<div style="animation: slideUp 0.3s ease-out;">${html}</div>`;
                })
                .catch(error => {
                    document.getElementById('output').innerHTML = `
                        <div style="animation: slideUp 0.3s ease-out;">
                            <h3 class="error" style="font-size: 20px; margin-bottom: 16px;">❌ Report Generation Error</h3>
                            <p style="font-size: 15px; color: var(--gray-700);">${error}</p>
                        </div>
                    `;
                });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def home():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('auth.login'))

@app.route('/dashboard')
@login_required
def dashboard():
    if not current_user.has_access():
        return redirect(url_for('billing.subscribe'))
    
    trial_active = current_user.is_trial_active()
    days_left = (current_user.trial_ends_at - datetime.utcnow()).days if trial_active else 0
    
    # Check if user has connected Shopify
    from models import ShopifyStore
    has_shopify = ShopifyStore.query.filter_by(user_id=current_user.id, is_active=True).first() is not None
    
    return render_template_string(DASHBOARD_HTML, trial_active=trial_active, days_left=days_left, is_subscribed=current_user.is_subscribed, has_shopify=has_shopify)

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "service": "Employee Suite", "version": "2.0"})

@app.route('/api/process_orders', methods=['GET', 'POST'])
@login_required
def api_process_orders():
    try:
        result = process_orders()
        return jsonify({"message": result, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/update_inventory', methods=['GET', 'POST'])
@login_required
def api_update_inventory():
    try:
        result = update_inventory()
        return jsonify({"message": result, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/generate_report', methods=['GET', 'POST'])
@login_required
def api_generate_report():
    try:
        data = generate_report()
        if 'error' in data:
            return f"<h3 class='error'>❌ Error: {data['error']}</h3>", 500
        
        html = '<style>.report-item{padding:15px;border-bottom:1px solid #eee;display:flex;justify-content:space-between}.report-item strong{color:#667eea}.total{font-size:1.3em;color:#28a745;margin-top:20px;padding:20px;background:#f8f9fa;border-radius:8px;text-align:center}.stat{margin:10px 0}</style><h3 class="success">📊 Revenue Report</h3>'
        
        if len(data['products']) == 0:
            html += '<p style="text-align:center;color:#999;padding:40px;">No products found. Connect your Shopify store first.</p>'
        else:
            for product in data['products']:
                html += f'<div class="report-item"><strong>{product["name"]}</strong><span>Stock: {product["stock"]} | Revenue: {product["revenue"]}</span></div>'
        
        html += f'<div class="total">'
        html += f'<div class="stat">💰 Total Revenue: <strong>{data["total_revenue"]}</strong></div>'
        html += f'<div class="stat">📦 Total Products: <strong>{data["total_products"]}</strong></div>'
        if 'total_orders' in data:
            html += f'<div class="stat">🛍️ Total Orders: <strong>{data["total_orders"]}</strong></div>'
        html += f'</div>'
        return html
    except Exception as e:
        return f"<h3 class='error'>❌ Error: {str(e)}</h3>", 500

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found", "status": 404}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error", "status": 500}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
