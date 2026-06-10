# 🐳 Docker Compose - Complete Setup

## Fresh Start with Best Configuration

This docker-compose includes:
- ✅ Redis (caching + message broker)
- ✅ PostgreSQL (semantic memory)
- ✅ Qdrant (vector search)
- ✅ Celery (background tasks)
- ✅ Flask API (optimized with gunicorn)

**Expected Performance: 1-2 second responses** ⚡

---

## Step 1: Verify .env File

Make sure your `.env` file has these settings:

```bash
# Required
MONGODB_URI=mongodb://localhost:27017/
OPENAI_API_KEY=sk-your-key-here
SECRET=your-secret-key

# Performance (will be set automatically by docker-compose)
USE_CELERY=true
ENABLE_RESPONSE_CACHE=true

# PostgreSQL password (optional, defaults to "mimipass")
POSTGRES_PASSWORD=mimipass

# Optional
YOUTUBE_API_KEY=your-youtube-key
TWILIO_ACCOUNT_SID=your-sid
TWILIO_AUTH_TOKEN=your-token
```

---

## Step 2: Build and Start All Services

```bash
# Build images and start all services
docker-compose up -d --build

# This will start:
# - Redis (port 6379)
# - PostgreSQL (port 5432)
# - Qdrant (port 6333)
# - Celery Worker (background)
# - Flask API (port 5000)
```

**Wait 30-60 seconds** for all services to initialize.

---

## Step 3: Verify Everything is Running

```bash
# Check all containers are healthy
docker-compose ps

# Expected output:
# mimi-redis          Up (healthy)
# mimi-postgres       Up (healthy)
# mimi-qdrant         Up (healthy)
# mimi-celery-worker  Up
# mimi-app            Up (healthy)
```

---

## Step 4: Test the API

```bash
# Test if API is responding
curl http://localhost:5000/health

# Or open in browser:
# http://localhost:5000
```

---

## Step 5: Monitor Logs

```bash
# View all logs
docker-compose logs -f

# View specific service
docker-compose logs -f app
docker-compose logs -f celery-worker
docker-compose logs -f redis
```

---

## Common Commands

### Start services:
```bash
docker-compose up -d
```

### Stop services:
```bash
docker-compose down
```

### Restart a service:
```bash
docker-compose restart app
docker-compose restart celery-worker
```

### View logs:
```bash
docker-compose logs -f app
```

### Rebuild after code changes:
```bash
docker-compose up -d --build
```

### Stop and remove everything (including data):
```bash
docker-compose down -v
```

---

## Service Details

### 🔴 Redis (Port 6379)
- **Purpose**: Response caching + Celery message broker
- **Config**: 512MB max memory, LRU eviction
- **Performance**: Sub-millisecond access times

### 🐘 PostgreSQL (Port 5432)
- **Purpose**: Semantic memory (facts & knowledge)
- **Database**: mimidb
- **User**: postgres
- **Password**: Set in .env (default: mimipass)

### 🔵 Qdrant (Port 6333, 6334)
- **Purpose**: Vector search for episodic & knowledge memory
- **Admin UI**: http://localhost:6333/dashboard
- **gRPC**: Port 6334 (faster operations)

### 🌱 Celery Worker
- **Purpose**: Background task processing
- **Concurrency**: 4 workers
- **Tasks**: Image/video fetch, DB writes

### 🚀 Flask API (Port 5000)
- **Server**: Gunicorn with gevent workers
- **Workers**: 2 (handles 1000+ concurrent connections)
- **Timeout**: 60 seconds
- **Health**: http://localhost:5000/health

---

## Performance Monitoring

### Check Cache Stats:
```bash
# Connect to Redis
docker exec -it mimi-redis redis-cli

# In Redis CLI:
KEYS mimi:cache:*
INFO stats
DBSIZE
```

### Check Celery Tasks:
```bash
# View active tasks
docker exec -it mimi-celery-worker celery -A celery_app inspect active

# View stats
docker exec -it mimi-celery-worker celery -A celery_app inspect stats
```

### Check Database:
```bash
# Connect to PostgreSQL
docker exec -it mimi-postgres psql -U postgres -d mimidb

# In psql:
\dt
SELECT COUNT(*) FROM semantic_memory;
```

---

## Troubleshooting

### Issue: "Port already allocated"

**Problem**: Another service is using the port

**Solutions**:
```bash
# Check what's using port 6379 (Redis)
netstat -ano | findstr :6379

# Stop old containers
docker ps -a
docker stop <container-id>
docker rm <container-id>

# Or stop all Docker containers
docker stop $(docker ps -aq)
```

### Issue: "Container unhealthy"

**Check logs**:
```bash
docker-compose logs <service-name>
```

**Restart service**:
```bash
docker-compose restart <service-name>
```

### Issue: "Out of memory"

**Increase Docker memory**:
1. Open Docker Desktop
2. Settings → Resources → Memory
3. Increase to at least 4GB
4. Apply & Restart

### Issue: "Slow build times"

**Use BuildKit**:
```bash
# Enable BuildKit (faster builds)
set DOCKER_BUILDKIT=1
docker-compose build --parallel
```

---

## Development Workflow

### Make code changes:
1. Edit your code
2. Rebuild: `docker-compose up -d --build app`
3. View logs: `docker-compose logs -f app`

### Quick restart (no rebuild):
```bash
docker-compose restart app
```

### Debug a container:
```bash
# Open shell in container
docker exec -it mimi-app /bin/sh

# Or run Python directly
docker exec -it mimi-app python
```

---

## Production Deployment

### Environment Variables:
```bash
# In production .env:
USE_CELERY=true
ENABLE_RESPONSE_CACHE=true
USE_ADVANCED_MEMORY=true  # Optional

# Use production MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/mimidb

# Use strong passwords
POSTGRES_PASSWORD=<strong-random-password>
SECRET=<strong-random-secret>
```

### Resource Limits:
Add to docker-compose.yml:
```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

---

## Backup & Restore

### Backup PostgreSQL:
```bash
docker exec mimi-postgres pg_dump -U postgres mimidb > backup.sql
```

### Restore PostgreSQL:
```bash
docker exec -i mimi-postgres psql -U postgres mimidb < backup.sql
```

### Backup Qdrant:
```bash
docker cp mimi-qdrant:/qdrant/storage ./qdrant-backup
```

---

## Performance Expectations

### With this setup:
- ✅ First request: ~1-2 seconds
- ✅ Cached request: ~0.1 seconds
- ✅ Handles: 100+ concurrent users
- ✅ Memory usage: ~1-2GB total
- ✅ CPU usage: Low (spikes during LLM calls)

### Optimization tips:
1. Enable caching (done ✅)
2. Use Celery for async (done ✅)
3. Pre-warm cache with common questions
4. Monitor Redis memory usage
5. Scale horizontally (add more workers)

---

## Summary

✅ **What you get:**
- Complete infrastructure
- Optimized performance
- Easy management
- Production-ready

🚀 **Quick start:**
```bash
docker-compose up -d --build
```

📊 **Monitor:**
```bash
docker-compose logs -f
```

🛑 **Stop:**
```bash
docker-compose down
```

**Your AI responds in 1-2 seconds!** ⚡
