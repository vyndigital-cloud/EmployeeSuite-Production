from flask import Blueprint, render_template_string

faq_bp = Blueprint('faq', __name__)

from flask import Blueprint, render_template, request
import os

faq_bp = Blueprint('faq', __name__)

@faq_bp.route('/faq')
def faq():
    shop = request.args.get('shop', '')
    host = request.args.get('host', '')
    return render_template('faq.html', 
                         shop=shop, 
                         host=host, 
                         config_api_key=os.getenv('SHOPIFY_API_KEY'))
