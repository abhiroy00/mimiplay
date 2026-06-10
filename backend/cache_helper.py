"""
Redis Cache Helper for Response Caching
Dramatically improves response time for repeated questions
"""

import os
import json
import logging
import hashlib

logger = logging.getLogger(__name__)

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("[Cache] Redis not available - caching disabled")


class ResponseCache:
    """
    Cache LLM responses in Redis for fast retrieval
    Similar questions get instant responses
    """
    
    def __init__(self, ttl=3600):
        self.ttl = ttl  # Cache TTL in seconds (1 hour default)
        self.enabled = False
        
        if REDIS_AVAILABLE:
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()
                self.enabled = True
                logger.info("[Cache] Redis cache enabled (TTL: %ds)", ttl)
            except Exception as e:
                logger.warning("[Cache] Redis connection failed: %s", e)
                self.enabled = False
    
    def _make_key(self, query, context_hash=None):
        """Generate cache key from query and optional context"""
        # Create hash from query (normalized)
        normalized = query.lower().strip()
        query_hash = hashlib.md5(normalized.encode()).hexdigest()[:16]
        
        if context_hash:
            return f"mimi:cache:{query_hash}:{context_hash}"
        return f"mimi:cache:{query_hash}"
    
    def get(self, query, context=None):
        """Get cached response if available"""
        if not self.enabled:
            return None
        
        try:
            context_hash = hashlib.md5(str(context).encode()).hexdigest()[:8] if context else None
            key = self._make_key(query, context_hash)
            
            cached = self.redis.get(key)
            if cached:
                logger.info("[Cache] HIT for query: %s", query[:50])
                return json.loads(cached)
            
            logger.info("[Cache] MISS for query: %s", query[:50])
            return None
        except Exception as e:
            logger.error("[Cache] Get failed: %s", e)
            return None
    
    def set(self, query, response, context=None):
        """Cache a response"""
        if not self.enabled:
            return False
        
        try:
            context_hash = hashlib.md5(str(context).encode()).hexdigest()[:8] if context else None
            key = self._make_key(query, context_hash)
            
            self.redis.setex(
                key,
                self.ttl,
                json.dumps(response)
            )
            logger.info("[Cache] Stored response for query: %s", query[:50])
            return True
        except Exception as e:
            logger.error("[Cache] Set failed: %s", e)
            return False
    
    def invalidate(self, pattern="mimi:cache:*"):
        """Invalidate cache entries matching pattern"""
        if not self.enabled:
            return 0
        
        try:
            keys = self.redis.keys(pattern)
            if keys:
                count = self.redis.delete(*keys)
                logger.info("[Cache] Invalidated %d cache entries", count)
                return count
            return 0
        except Exception as e:
            logger.error("[Cache] Invalidate failed: %s", e)
            return 0
    
    def stats(self):
        """Get cache statistics"""
        if not self.enabled:
            return {"enabled": False}
        
        try:
            info = self.redis.info("stats")
            return {
                "enabled": True,
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_keys": len(self.redis.keys("mimi:cache:*")),
            }
        except Exception as e:
            logger.error("[Cache] Stats failed: %s", e)
            return {"enabled": True, "error": str(e)}


# Global cache instance
_cache_instance = None

def get_cache():
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        # Only enable cache if explicitly set
        cache_enabled = os.environ.get("ENABLE_RESPONSE_CACHE", "true").lower() == "true"
        if cache_enabled:
            _cache_instance = ResponseCache(ttl=3600)  # 1 hour TTL
        else:
            logger.info("[Cache] Response caching disabled")
            _cache_instance = ResponseCache(ttl=0)
            _cache_instance.enabled = False
    return _cache_instance


if __name__ == "__main__":
    # Test caching
    logging.basicConfig(level=logging.INFO)
    
    cache = get_cache()
    
    if cache.enabled:
        # Test set/get
        test_query = "What is photosynthesis?"
        test_response = {"text": "Photosynthesis is how plants make food", "image_url": None}
        
        cache.set(test_query, test_response)
        retrieved = cache.get(test_query)
        
        print(f"Cached: {retrieved}")
        print(f"Stats: {cache.stats()}")
    else:
        print("Cache not available")
