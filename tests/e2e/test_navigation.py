
import pytest
from playwright.sync_api import Page, expect

def test_navigation_settings(page: Page):
    """
    Critical Path: Verify dashboard navigation to Settings.
    Ensures URL is constructed correctly (no 'apps//settings' malformation).
    """
    # 1. Simulate a local dev environment visit
    # The app renders a 'demo' dashboard if ENVIRONMENT != production and no shop params
    # We assume the test runner will access localhost:5000
    
    # Verify the page loads
    response = page.goto("http://localhost:5000/dashboard")
    assert response.ok
    
    # 2. Check for the Settings link
    # We look for the link with the text 'Settings' in the quick menu or sidebar
    # The 'quick-menu-item' for Settings or the side 'nav-btn'
    
    # Let's focus on the side nav-btn as it's always visible in desktop view
    settings_link = page.get_by_role("link", name="Settings").first
    expect(settings_link).to_be_visible()
    
    # 3. Click and Verify Navigation
    # The click should trigger internalNav -> window.location.href
    # We expect to be redirected to /settings/shopify?shop=...
    
    with page.expect_navigation(url="**/settings/shopify*"):
        settings_link.click()
        
    # 4. Verify Success
    # App Bridge might rewrite the URL to https://admin.shopify.com/...
    # or keep it as localhost:... depending on environment.
    # The CRITICAL check is that we didn't get the double slash.
    assert "apps//settings" not in page.url
    
    # If we are on admin.shopify.com, navigation clearly worked via Bridge
    # If we are on localhost, we MUST have the shop param
    if "localhost" in page.url:
        assert "shop=" in page.url
        assert "/settings/shopify" in page.url
    

def test_root_gate_redirect(page: Page):
    """
    Verify the Root Gate correctly redirects to the dashboard.
    """
    # Visit root with shop/host
    response = page.goto("http://localhost:5000/?shop=test.myshopify.com&host=testhost")
    assert response.ok
    
    # It should land on /features/dashboard
    # Note: app_bridge_redirect uses JS to redirect
    page.wait_for_url("**/features/dashboard*")
    assert "/features/dashboard" in page.url
    assert "shop=test.myshopify.com" in page.url
    assert "host=testhost" in page.url
    
    print(f"✅ Root Gate Successful! Led to: {page.url}")

def test_features_welcome_load(page: Page):
    """
    Verify the /features/welcome page (newly registered blueprint) loads correctly.
    """
    response = page.goto("http://localhost:5000/features/welcome?shop=test.myshopify.com&host=testhost")
    assert response.ok
    
    # Check for content on the welcome page
    expect(page.get_by_text("Automate Your Store")).to_be_visible()
    
    print(f"✅ Features Welcome Page Loads! URL: {page.url}")
