"""
Configuration Checker - Validates your .env setup
Run this to verify everything is configured correctly
"""

import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

def check_config():
    print("\n" + "="*70)
    print("🔍 MIMI AI CONFIGURATION CHECK")
    print("="*70 + "\n")
    
    issues = []
    warnings = []
    success = []
    
    # Required configurations
    print("📋 REQUIRED SETTINGS:")
    print("-" * 70)
    
    # MongoDB
    mongodb_uri = os.getenv("MONGODB_URI")
    if mongodb_uri:
        print(f"✅ MONGODB_URI: {mongodb_uri[:30]}...")
        success.append("MongoDB URI configured")
    else:
        print("❌ MONGODB_URI: NOT SET")
        issues.append("MONGODB_URI is required")
    
    # Secret Key
    secret = os.getenv("SECRET")
    if secret:
        print(f"✅ SECRET: {'*' * 20} (length: {len(secret)})")
        if len(secret) < 20:
            warnings.append("SECRET is too short (should be 20+ characters)")
        success.append("JWT Secret configured")
    else:
        print("❌ SECRET: NOT SET")
        issues.append("SECRET is required for JWT authentication")
    
    # OpenAI API Key
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    if openai_key:
        masked = openai_key[:10] + "..." + openai_key[-6:]
        print(f"✅ OPENAI_API_KEY: {masked}")
        success.append("OpenAI API key configured")
    else:
        print("⚠️  OPENAI_API_KEY: NOT SET")
    
    if anthropic_key and anthropic_key != "your_anthropic_key_here":
        masked = anthropic_key[:10] + "..." + anthropic_key[-6:]
        print(f"✅ ANTHROPIC_API_KEY: {masked}")
        success.append("Anthropic API key configured")
    else:
        print("⚠️  ANTHROPIC_API_KEY: NOT SET (optional)")
    
    if not openai_key and not anthropic_key:
        issues.append("At least one LLM API key (OpenAI or Anthropic) is required")
    
    print()
    
    # Performance settings
    print("⚡ PERFORMANCE SETTINGS:")
    print("-" * 70)
    
    # Caching
    cache_enabled = os.getenv("ENABLE_RESPONSE_CACHE", "false").lower() == "true"
    if cache_enabled:
        print("✅ ENABLE_RESPONSE_CACHE: true")
        success.append("Response caching enabled")
        
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            print(f"✅ REDIS_URL: {redis_url}")
            
            # Test Redis connection
            try:
                import redis
                r = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
                r.ping()
                print("✅ Redis Connection: SUCCESS")
                success.append("Redis is accessible")
            except ImportError:
                warnings.append("redis package not installed (pip install redis)")
            except Exception as e:
                warnings.append(f"Redis connection failed: {str(e)[:50]}")
                print(f"⚠️  Redis Connection: FAILED - {str(e)[:50]}")
        else:
            warnings.append("REDIS_URL not set - caching will not work")
    else:
        print("⚠️  ENABLE_RESPONSE_CACHE: false (caching disabled)")
        warnings.append("Response caching is disabled - responses will be slower")
    
    # Celery
    celery_enabled = os.getenv("USE_CELERY", "false").lower() == "true"
    if celery_enabled:
        print("✅ USE_CELERY: true")
        success.append("Async processing enabled")
    else:
        print("⚠️  USE_CELERY: false (async processing disabled)")
        warnings.append("Celery is disabled - media will be fetched synchronously")
    
    print()
    
    # Optional settings
    print("🔧 OPTIONAL SETTINGS:")
    print("-" * 70)
    
    youtube_key = os.getenv("YOUTUBE_API_KEY")
    if youtube_key and youtube_key != "your_youtube_key":
        print(f"✅ YOUTUBE_API_KEY: {youtube_key[:10]}...")
        success.append("YouTube API configured")
    else:
        print("⚠️  YOUTUBE_API_KEY: NOT SET (video search disabled)")
    
    # Advanced memory
    advanced_memory = os.getenv("USE_ADVANCED_MEMORY", "false").lower() == "true"
    if advanced_memory:
        print("✅ USE_ADVANCED_MEMORY: true")
        
        db_url = os.getenv("DATABASE_URL")
        qdrant_url = os.getenv("QDRANT_URL")
        
        if db_url:
            print(f"✅ DATABASE_URL: {db_url[:40]}...")
        else:
            issues.append("DATABASE_URL required for advanced memory")
        
        if qdrant_url:
            print(f"✅ QDRANT_URL: {qdrant_url}")
        else:
            issues.append("QDRANT_URL required for advanced memory")
    else:
        print("⚠️  USE_ADVANCED_MEMORY: false (using basic memory)")
    
    print()
    
    # Summary
    print("="*70)
    print("📊 SUMMARY")
    print("="*70)
    
    if success:
        print(f"\n✅ Working ({len(success)}):")
        for s in success[:5]:  # Show first 5
            print(f"   • {s}")
        if len(success) > 5:
            print(f"   ... and {len(success) - 5} more")
    
    if warnings:
        print(f"\n⚠️  Warnings ({len(warnings)}):")
        for w in warnings:
            print(f"   • {w}")
    
    if issues:
        print(f"\n❌ Critical Issues ({len(issues)}):")
        for i in issues:
            print(f"   • {i}")
        print("\n❌ Fix these issues before starting the app!")
        return False
    else:
        print("\n✅ Configuration looks good!")
        
        # Performance estimate
        print("\n⚡ Expected Performance:")
        if cache_enabled and celery_enabled:
            print("   • First request: ~1-2 seconds")
            print("   • Cached request: ~0.1 seconds ⚡⚡⚡")
            print("   • Mode: OPTIMIZED")
        elif cache_enabled:
            print("   • First request: ~3-5 seconds")
            print("   • Cached request: ~0.1 seconds ⚡")
            print("   • Mode: CACHING ONLY")
        else:
            print("   • All requests: ~5-9 seconds")
            print("   • Mode: BASIC (no optimization)")
        
        print("\n🚀 Ready to start!")
        print("   Run: python app.py")
        print("   Or: docker-compose up -d")
        
        return True
    
    print()

if __name__ == "__main__":
    try:
        check_config()
    except Exception as e:
        print(f"\n❌ Error checking configuration: {e}")
        import traceback
        traceback.print_exc()
