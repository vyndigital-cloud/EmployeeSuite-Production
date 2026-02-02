import os
from flask import Flask, render_template
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='/Users/essentials/MissionControl/templates', static_folder='/Users/essentials/MissionControl/static')
app.config['SECRET_KEY'] = 'test_key'

# Mock config
os.environ['SHOPIFY_API_KEY'] = 'test_api_key'

@app.route('/')
def test_render():
    try:
        with app.test_request_context():
            html = render_template(
                'subscribe.html',
                trial_active=False,
                has_access=False,
                days_left=0,
                is_subscribed=False,
                shop='test.myshopify.com',
                host='test_host',
                has_store=True,
                plan='pro',
                plan_name='Employee Suite Pro',
                price=39,
                features=['Feature 1', 'Feature 2'],
                error=None,
                config_api_key='test_api_key'
            )
            print("Template rendered successfully!")
            return "OK"
    except Exception as e:
        print(f"Error rendering template: {e}")
        return "Error"

if __name__ == "__main__":
    with app.app_context():
        test_render()
