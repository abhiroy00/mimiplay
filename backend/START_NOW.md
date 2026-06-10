# 🚀 Start Your Optimized Mimi AI NOW

## Your Current Setup ✅

You already have:
- ✅ Redis running (port 6379)
- ✅ MongoDB configured
- ✅ OpenAI API key
- ✅ Performance features enabled in .env

## Quick Start (2 Options)

### Option 1: Run Without Docker (Fastest - Recommended)

Since you already have Redis running, just start the Flask app directly:

```bash
# Start the app with performance features
python app.py
```

**That's it!** Your API is now running with:
- ✅ Response caching (via existing Redis)
- ✅ Async processing ready (Celery can be added later)
- ✅ 1-2 second response time

Test it:
```bash
python test_live_memory.py
```

---

### Option 2: Add Docker Services (PostgreSQL + Qdrant)

If you want the full advanced memory system:

```bash
# Start PostgreSQL and Qdrant only (uses your existing Redis)
docker-compose -f docker-compose.simple.yml up -d

# Wait 10 seconds for services to start
timeout /t 10

# Check services
docker-compose -f docker-compose.simple.yml ps

# Start Celery worker in a new terminal
celery -A celery_app worker --loglevel=info --concurrency=4

# Start the app in another terminal
python app.py
```

---

## Current Performance Status

Your `.env` is configured for **OPTIMIZED MODE**:

```
ENABLE_RESPONSE_CACHE=true  ✅
USE_CELERY=true             ✅
REDIS_URL=redis://localhost:6379/0  ✅
```

**Expected Performance:**
- First request: ~2-3 seconds
- Cached request: ~0.1 seconds ⚡⚡⚡
- With Celery: ~1-2 seconds

---

## Test Performance Right Now

### Test 1: Basic Test
```bash
python test_live_memory.py
```

### Test 2: Check Cache Working
```bash
# Run twice - second should be instant
python -c "from mimi_llm_session import MimiLLMSession; import time; s=MimiLLMSession(session_id='test1'); start=time.time(); s.process_text('What is gravity?'); print(f'Time: {time.time()-start:.2f}s')"
```

### Test 3: Verify Config
```bash
python check_config.py
```

---

## Troubleshooting

### Issue: "Port 6379 already in use"
✅ **Solution**: You already have Redis running! This is good.
   - Just use Option 1 (run without Docker)
   - Or use `docker-compose.simple.yml` which uses your existing Redis

### Issue: "Redis connection failed"
```bash
# Check if Redis is running
docker ps | findstr redis

# Should show: innovativeais_redis
```

### Issue: "Module not found"
```bash
# Install missing packages
pip install redis celery
```

---

## What's Running

### Currently Active:
- ✅ Redis (innovativeais_redis) on port 6379
- ✅ MongoDB on localhost:27017

### To Add (Optional):
- PostgreSQL (port 5432) - Advanced memory
- Qdrant (port 6333) - Vector search
- Celery Worker - Background tasks

---

## Commands Quick Reference

### Start the app:
```bash
python app.py
```

### Test performance:
```bash
python test_live_memory.py
```

### Check configuration:
```bash
python check_config.py
```

### Start Docker services (optional):
```bash
docker-compose -f docker-compose.simple.yml up -d
```

### Stop Docker services:
```bash
docker-compose -f docker-compose.simple.yml down
```

### View logs:
```bash
docker-compose -f docker-compose.simple.yml logs -f
```

---

## Performance Monitoring

### Check Cache Stats:
```python
from cache_helper import get_cache
cache = get_cache()
print(cache.stats())
```

### Monitor Redis:
```bash
docker exec -it innovativeais_redis redis-cli

# In Redis CLI:
KEYS mimi:cache:*
INFO stats
```

---

## Next Steps

1. **Right Now**: Start the app
   ```bash
   python app.py
   ```

2. **Test It**: Run the test script
   ```bash
   python test_live_memory.py
   ```

3. **Monitor**: Watch the response times

4. **Optional**: Add Celery for even better performance
   ```bash
   # In a new terminal:
   celery -A celery_app worker --loglevel=info
   ```

---

## Summary

✅ **You're ready to go!**

Your setup:
- Redis: Running ✅
- Config: Optimized ✅
- Dependencies: Installed ✅

**Just run:**
```bash
python app.py
```

**And test:**
```bash
python test_live_memory.py
```

Expected result: **1-2 second responses!** ⚡

---

## Questions?

- Configuration issues: Run `python check_config.py`
- Performance issues: Check `PERFORMANCE_QUICKSTART.md`
- Docker issues: Use `docker-compose.simple.yml`
- Full setup: Read `PERFORMANCE_OPTIMIZATION.md`
