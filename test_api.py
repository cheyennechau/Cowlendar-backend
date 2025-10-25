"""
Quick test script for Cowlendar API endpoints.
Run this after starting the server to verify everything works.
"""
import requests
import json
from time import sleep

BASE_URL = "http://localhost:8000"

def test_status():
    """Test the status endpoint"""
    print("\n1. Testing GET /status...")
    response = requests.get(f"{BASE_URL}/status")
    print(f"   Status: {response.status_code}")
    data = response.json()
    print(f"   Authenticated: {data.get('authed')}")
    print(f"   Today's mood: {data.get('today', {}).get('mood')}")
    print(f"   Message: {data.get('today', {}).get('message')}")
    return data

def test_google_auth_start():
    """Get Google OAuth URL"""
    print("\n2. Testing GET /auth/google/start...")
    response = requests.get(f"{BASE_URL}/auth/google/start")
    print(f"   Status: {response.status_code}")
    data = response.json()
    auth_url = data.get('auth_url')
    if auth_url:
        print(f"   ✓ Got auth URL")
        print(f"\n   📋 Open this URL in your browser to authenticate:")
        print(f"   {auth_url}\n")
    return data

def test_mcp_refresh():
    """Test MCP-powered mood refresh"""
    print("\n3. Testing POST /mood/refresh/mcp...")
    try:
        response = requests.post(f"{BASE_URL}/mood/refresh/mcp")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✓ Percent done: {data.get('percent_done')}%")
            print(f"   ✓ Mood: {data.get('mood')}")
            print(f"   ✓ Message: {data.get('message')}")
            print(f"   ✓ Milk points: {data.get('milk_points')}")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")

def test_notion_databases():
    """Test Notion database listing"""
    print("\n4. Testing GET /notion/databases...")
    try:
        response = requests.get(f"{BASE_URL}/notion/databases?page_size=5")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            results = data.get('results', [])
            print(f"   ✓ Found {len(results)} databases")
            for db in results[:3]:
                title = db.get('title', [{}])[0].get('plain_text', 'Untitled')
                print(f"     - {title}")
        else:
            print(f"   ✗ Error: {response.text}")
    except Exception as e:
        print(f"   ✗ Exception: {e}")

def main():
    print("=" * 60)
    print("🐮 COWLENDAR API TEST SUITE")
    print("=" * 60)
    
    # Test 1: Status
    status_data = test_status()
    is_authed = status_data.get('authed', False)
    
    # Test 2: Google Auth (if not authenticated)
    if not is_authed:
        print("\n⚠️  Not authenticated with Google Calendar")
        test_google_auth_start()
        print("\n   After authenticating, run this script again.")
        return
    
    print("\n✓ Authenticated with Google Calendar")
    
    # Test 3: MCP Refresh
    test_mcp_refresh()
    
    # Test 4: Notion (optional)
    test_notion_databases()
    
    print("\n" + "=" * 60)
    print("✓ Test suite complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Wait 5 minutes for the background scheduler to run")
    print("2. Check /status again to see updated mood")
    print("3. Build your Chrome extension to poll /status")
    print("\n")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Could not connect to server")
        print("   Make sure the server is running:")
        print("   uvicorn app.main:app --reload --port 8000\n")
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
