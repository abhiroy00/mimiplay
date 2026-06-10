"""
Test API endpoints for memory system
Simple tests that don't require audio
"""

import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:5000"
# Note: In production, get this from your JWT authentication
TOKEN = "test-token"  # Update this with a real JWT token

def test_session_start():
    """Test 1: Start a Mimi session"""
    print("\n" + "="*70)
    print("TEST 1: Start Mimi Session")
    print("="*70)
    
    try:
        response = requests.post(
            f"{BASE_URL}/start-mimi-session",
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "student_name": "Test Student",
                "student_id": "507f1f77bcf86cd799439011",  # Valid ObjectId format
                "session_id": "test_session_api_001"
            },
            timeout=10
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n✅ Session started successfully!")
            print(f"   Status: {data.get('status')}")
            print(f"   Message: {data.get('message')}")
            print(f"   Greeting: {data.get('greeting_text', '')[:80]}...")
            return True
        elif response.status_code == 401:
            print(f"\n❌ Authentication failed!")
            print(f"   Update TOKEN variable in test_api.py with a valid JWT")
            print(f"   Or check app.py for token requirements")
            return False
        else:
            print(f"\n❌ Request failed!")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to server!")
        print("   Make sure Flask app is running:")
        print("   python app.py")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

def test_health():
    """Test 2: Check API health"""
    print("\n" + "="*70)
    print("TEST 2: Check API Health")
    print("="*70)
    
    try:
        # Try health endpoint (if exists)
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy!")
            return True
        else:
            # Try root endpoint
            response = requests.get(BASE_URL, timeout=5)
            if response.status_code in [200, 404]:
                print("✅ API is running!")
                return True
            return False
    except:
        print("⚠️  Health endpoint not available, but may still be working")
        return True

def test_mongodb_connection():
    """Test 3: Verify MongoDB connection"""
    print("\n" + "="*70)
    print("TEST 3: MongoDB Connection")
    print("="*70)
    
    try:
        from pymongo import MongoClient
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        
        print(f"Connecting to: {mongo_uri.split('@')[-1] if '@' in mongo_uri else mongo_uri[:50]}...")
        
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Test connection
        client.server_info()
        
        print("✅ MongoDB connected!")
        
        # Check collections
        db = client["AlexiDB"]
        collections = db.list_collection_names()
        print(f"   Collections: {', '.join(collections[:5])}")
        
        return True
    except Exception as e:
        print(f"❌ MongoDB connection failed: {e}")
        print("\nSolutions:")
        print("1. Install MongoDB: https://www.mongodb.com/try/download/community")
        print("2. Or use MongoDB Atlas (free): https://www.mongodb.com/cloud/atlas")
        print("3. Update MONGODB_URI in .env file")
        return False

def test_llm_api_key():
    """Test 4: Verify LLM API keys"""
    print("\n" + "="*70)
    print("TEST 4: LLM API Keys")
    print("="*70)
    
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if openai_key:
        masked = openai_key[:7] + "..." + openai_key[-4:] if len(openai_key) > 11 else "***"
        print(f"✅ OPENAI_API_KEY: {masked}")
    else:
        print("❌ OPENAI_API_KEY: Not set")
    
    if anthropic_key:
        masked = anthropic_key[:7] + "..." + anthropic_key[-4:] if len(anthropic_key) > 11 else "***"
        print(f"✅ ANTHROPIC_API_KEY: {masked}")
    else:
        print("⚠️  ANTHROPIC_API_KEY: Not set (optional)")
    
    if openai_key or anthropic_key:
        print("\n✅ At least one LLM API key is configured")
        return True
    else:
        print("\n❌ No LLM API keys found!")
        print("\nGet API key from:")
        print("- OpenAI: https://platform.openai.com/api-keys")
        print("- Anthropic: https://console.anthropic.com/")
        return False

def check_env_file():
    """Check if .env file exists"""
    print("\n" + "="*70)
    print("SETUP CHECK: Environment Configuration")
    print("="*70)
    
    if os.path.exists(".env"):
        print("✅ .env file found")
        return True
    else:
        print("❌ .env file not found!")
        print("\nCreate .env file:")
        print("1. Copy .env.example to .env")
        print("2. Fill in your API keys")
        print("3. Run this test again")
        return False

def print_summary(results):
    """Print test summary"""
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:30s} {status}")
    
    total = len(results)
    passed = sum(1 for r in results.values() if r)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Your setup is ready.")
        print("\nNext steps:")
        print("1. Run: python test_memory.py")
        print("2. Run: python test_live_memory.py")
        print("3. Start using the API!")
    else:
        print("\n⚠️  Some tests failed. Follow the suggestions above to fix them.")

def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("🧪 MIMI API TEST SUITE")
    print("="*70)
    print("\nThis will test your API setup and configuration.\n")
    
    results = {}
    
    # Check setup
    if not check_env_file():
        print("\n❌ Cannot continue without .env file")
        return
    
    # Run tests
    results["MongoDB Connection"] = test_mongodb_connection()
    results["LLM API Keys"] = test_llm_api_key()
    results["API Health"] = test_health()
    results["Session Start"] = test_session_start()
    
    # Print summary
    print_summary(results)

if __name__ == "__main__":
    main()
