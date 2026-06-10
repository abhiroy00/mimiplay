# 🚀 Complete Setup & Testing Guide

Follow these steps to set up and test the memory system.

## Prerequisites

- Python 3.8+ installed
- MongoDB running (local or Atlas)
- OpenAI or Anthropic API key

## Part 1: Basic Setup (Required - 5 minutes)

### Step 1: Create .env File

Create a file named `.env` in the project root with:

```bash
# MongoDB Connection
MONGODB_URI=mongodb://localhost:27017/
# Or for MongoDB Atlas:
# MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/

# LLM API Keys (at least one required)
OPENAI_API_KEY=sk-your-openai-key-here
# ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# YouTube API (optional, for video search)
# YOUTUBE_API_KEY=your-youtube-api-key

# JWT Secret (required for authentication)
SECRET=your-secret-key-here-change-this

# Advanced Memory (optional - set to false for now)
USE_ADVANCED_MEMORY=false
```

### Step 2: Install Python Dependencies

```bash
# Navigate to project directory
cd c:\Users\abhis\Downloads\mimiplay-main\mimiplay-main

# Install requirements
pip install -r requirements.txt
```

### Step 3: Test Basic Memory

```bash
# Run the basic memory test
python test_memory.py
```

**Expected Output:**
```
============================================================
🧠 Testing LLM Conversation Memory
============================================================

Question 1: What is the solar system?
------------------------------------------------------------
Mimi: The solar system is our Sun and all planets...
💾 Memory: 2 messages in history

Question 2: How many planets are there?
------------------------------------------------------------
Mimi: There are 8 planets in our solar system...
💾 Memory: 4 messages in history

✅ Memory test completed!
```

### Step 4: Start the Application

```bash
# Start Flask app
python app.py
```

**Expected Output:**
```
[INFO] MimiLLMSession: OpenAI=True, Anthropic=False, Memory=basic
 * Running on http://127.0.0.1:5000
```

---

## Part 2: Test Basic Memory API (10 minutes)

Now let's test the API endpoints using the command line.

### Test 1: Start a Session

```bash
# Windows PowerShell
curl -X POST http://localhost:5000/start-mimi-session `
  -H "Authorization: Bearer test-token-change-this" `
  -H "Content-Type: application/json" `
  -d '{\"student_name\": \"Test Student\", \"student_id\": \"507f1f77bcf86cd799439011\", \"session_id\": \"test_session_001\"}'
```

**Expected Response:**
```json
{
  "status": "success",
  "message": "Mimi LLM session started",
  "greeting_text": "Hi Test Student! Great to see you...",
  "greeting_audio": "base64_audio_data..."
}
```

### Test 2: Send Text Message (Simpler Test)

Create a test file `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:5000"
TOKEN = "test-token-change-this"  # Update with your JWT token

def test_session_start():
    print("\n" + "="*60)
    print("TEST 1: Start Session")
    print("="*60)
    
    response = requests.post(
        f"{BASE_URL}/start-mimi-session",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        },
        json={
            "student_name": "Test Student",
            "student_id": "507f1f77bcf86cd799439011",
            "session_id": "test_session_001"
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.status_code == 200

def test_memory():
    print("\n" + "="*60)
    print("TEST 2: Test Memory with Text")
    print("="*60)
    
    # This would require audio file, so let's check the session exists
    # For now, we'll verify the session was created
    
    print("✅ Session created successfully!")
    print("\nNext: Test with audio using test_memory.py script")

if __name__ == "__main__":
    try:
        success = test_session_start()
        if success:
            test_memory()
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\nMake sure:")
        print("1. Flask app is running (python app.py)")
        print("2. MongoDB is accessible")
        print("3. OPENAI_API_KEY is set in .env")
```

Run it:
```bash
python test_api.py
```

---

## Part 3: Advanced Memory Setup (Optional - 30 minutes)

Only do this if you want the full 4-tier memory system.

### Step 1: Install Advanced Dependencies

```bash
pip install -r requirements_advanced_memory.txt
```

This installs:
- redis (Working Memory)
- psycopg2-binary (Semantic Memory)
- qdrant-client (Episodic & Knowledge Memory)
- sentence-transformers (Embeddings)

### Step 2: Install Docker Desktop

Download and install Docker Desktop for Windows:
https://www.docker.com/products/docker-desktop/

### Step 3: Start Services with Docker

```bash
# Start Redis (Working Memory)
docker run -d --name mimi-redis -p 6379:6379 redis:7-alpine

# Start PostgreSQL (Semantic Memory)
docker run -d --name mimi-postgres `
  -e POSTGRES_PASSWORD=mimipass `
  -e POSTGRES_DB=mimidb `
  -p 5432:5432 `
  postgres:15-alpine

# Start Qdrant (Episodic & Knowledge Memory)
docker run -d --name mimi-qdrant -p 6333:6333 qdrant/qdrant
```

### Step 4: Verify Services are Running

```bash
# Check Docker containers
docker ps

# Should show 3 containers:
# - mimi-redis (port 6379)
# - mimi-postgres (port 5432)
# - mimi-qdrant (port 6333)
```

### Step 5: Update .env File

Add these lines to your `.env`:

```bash
# Enable Advanced Memory
USE_ADVANCED_MEMORY=true

# Redis (Working Memory)
REDIS_URL=redis://localhost:6379/0

# PostgreSQL (Semantic Memory)
DATABASE_URL=postgresql://postgres:mimipass@localhost:5432/mimidb

# Qdrant (Episodic & Knowledge Memory)
QDRANT_URL=http://localhost:6333
```

### Step 6: Test Advanced Memory

```bash
python test_advanced_memory.py
```

**Expected Output:**
```
============================================================
🧪 ADVANCED MEMORY SYSTEM TEST SUITE
============================================================

🔍 Testing Dependencies
============================================================
redis                ✅ Available
psycopg2             ✅ Available
qdrant               ✅ Available
embeddings           ✅ Available
memory_system        ✅ Available

🔌 Testing Service Connections
============================================================
Redis           ✅ Connected
PostgreSQL      ✅ Connected
Qdrant          ✅ Connected

🧠 Testing Memory Router
============================================================
✅ Memory Router initialized successfully

⚡ Testing Working Memory (Redis)
============================================================
✅ Working Memory operational
   - Backend: redis
   - Messages stored: 2

📚 Testing Semantic Memory (PostgreSQL)
============================================================
✅ Semantic Memory operational
   - Backend: postgres
   - Facts stored: 3

🎬 Testing Episodic Memory (Qdrant)
============================================================
✅ Episodic Memory operational
   - Backend: qdrant
   - Interactions stored: 3

🎓 Testing Knowledge Memory (Qdrant)
============================================================
✅ Knowledge Memory operational
   - Backend: qdrant
   - Concepts stored: 3

📊 TEST SUMMARY
============================================================
Working Memory       ✅ PASS
Semantic Memory      ✅ PASS
Episodic Memory      ✅ PASS
Knowledge Memory     ✅ PASS
Context Building     ✅ PASS
Memory Updates       ✅ PASS

Total: 6/6 tests passed

🎉 All tests passed! Advanced memory system is fully operational.
```

### Step 7: Restart Application with Advanced Memory

```bash
# Stop the app (Ctrl+C)
# Restart
python app.py
```

**Expected Output:**
```
[INFO] [MimiLLM] Advanced multi-tier memory system available
[INFO] MimiLLMSession: OpenAI=True, Anthropic=False, Memory=advanced
```

---

## Part 4: Test Memory in Action

Let's test that memory actually works!

### Create Test Script: `test_live_memory.py`

```python
"""
Live test of memory system - simulates a conversation
"""
import os
from dotenv import load_dotenv
from mimi_llm_session import MimiLLMSession

load_dotenv()

def test_conversation():
    print("\n" + "="*60)
    print("🧪 Testing Live Memory System")
    print("="*60 + "\n")
    
    # Create session
    session = MimiLLMSession(
        student_name="Test Student",
        session_id="live_test_session",
        student_id="507f1f77bcf86cd799439011",
        student_age=10
    )
    
    print(f"Memory Mode: {session.memory_mode}")
    print()
    
    # Test conversation
    questions = [
        "What is the solar system?",
        "How many planets are there?",
        "Tell me about the biggest one",  # Should remember it's Jupiter
        "What color is it?",  # Should know we're talking about Jupiter
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"Q{i}: {question}")
        print("-" * 60)
        
        try:
            result = session.process_text(question)
            answer = result.get("text", "No response")
            
            print(f"Mimi: {answer}")
            
            # Show memory stats
            stats = session.get_memory_stats()
            print(f"💾 Memory: {stats['messages_in_memory']} messages")
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
    
    print("="*60)
    print("✅ Test Complete!")
    print("="*60)

if __name__ == "__main__":
    test_conversation()
```

Run it:
```bash
python test_live_memory.py
```

**Expected Output:**
```
============================================================
🧪 Testing Live Memory System
============================================================

Memory Mode: basic

Q1: What is the solar system?
------------------------------------------------------------
Mimi: The solar system is our Sun and all the planets that orbit it. There are 8 planets including Earth!
💾 Memory: 2 messages

Q2: How many planets are there?
------------------------------------------------------------
Mimi: There are 8 planets in our solar system. That's what we just talked about!
💾 Memory: 4 messages

Q3: Tell me about the biggest one
------------------------------------------------------------
Mimi: Jupiter is the biggest planet! It's so big that all other planets could fit inside it.
💾 Memory: 6 messages

Q4: What color is it?
------------------------------------------------------------
Mimi: Jupiter has orange, brown and white stripes with a big red spot!
💾 Memory: 8 messages

✅ Test Complete!
```

---

## Troubleshooting

### Issue: "OpenAI API key not found"

**Solution:**
1. Check `.env` file exists
2. Verify `OPENAI_API_KEY=sk-...` is set
3. Restart Python script

### Issue: "MongoDB connection failed"

**Solution:**
```bash
# Check if MongoDB is running
# If using local MongoDB:
net start MongoDB

# Or use MongoDB Atlas (cloud)
# Update MONGODB_URI in .env to your Atlas connection string
```

### Issue: "Module not found"

**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt

# If testing advanced memory
pip install -r requirements_advanced_memory.txt
```

### Issue: "Docker containers not starting"

**Solution:**
```bash
# Check Docker is running
docker --version

# Remove old containers
docker rm -f mimi-redis mimi-postgres mimi-qdrant

# Start again
docker run -d --name mimi-redis -p 6379:6379 redis:7-alpine
docker run -d --name mimi-postgres -e POSTGRES_PASSWORD=mimipass -e POSTGRES_DB=mimidb -p 5432:5432 postgres:15-alpine
docker run -d --name mimi-qdrant -p 6333:6333 qdrant/qdrant
```

### Issue: "Advanced memory using fallbacks"

**Solution:**
This is normal! Advanced memory gracefully falls back to MongoDB if services aren't available.

To use full advanced features:
1. Ensure all Docker containers are running
2. Check `USE_ADVANCED_MEMORY=true` in `.env`
3. Restart Flask app

---

## Quick Command Reference

### Start Everything
```bash
# 1. Start Docker services (if using advanced memory)
docker start mimi-redis mimi-postgres mimi-qdrant

# 2. Start Flask app
python app.py
```

### Test Everything
```bash
# Basic memory
python test_memory.py

# Advanced memory
python test_advanced_memory.py

# Live conversation
python test_live_memory.py
```

### Stop Everything
```bash
# Stop Flask app
Ctrl+C

# Stop Docker services
docker stop mimi-redis mimi-postgres mimi-qdrant
```

### View Logs
```bash
# Docker logs
docker logs mimi-redis
docker logs mimi-postgres
docker logs mimi-qdrant

# App logs
# Shown in terminal where python app.py is running
```

---

## Success Checklist

### Basic Memory (Minimum Required)
- [ ] `.env` file created with OPENAI_API_KEY
- [ ] `pip install -r requirements.txt` completed
- [ ] `python test_memory.py` passes
- [ ] `python app.py` starts successfully
- [ ] `python test_live_memory.py` shows context awareness

### Advanced Memory (Optional)
- [ ] Docker Desktop installed
- [ ] `pip install -r requirements_advanced_memory.txt` completed
- [ ] 3 Docker containers running (redis, postgres, qdrant)
- [ ] `.env` updated with USE_ADVANCED_MEMORY=true
- [ ] `python test_advanced_memory.py` all tests pass
- [ ] Flask app shows "Memory=advanced"

---

## What's Next?

### You're Ready To:
1. ✅ Use memory in your frontend application
2. ✅ Test with real students
3. ✅ Monitor conversation quality
4. ✅ Scale to production

### Future Enhancements:
1. Add more memory tiers
2. Implement knowledge graphs
3. Build analytics dashboard
4. Create student profiles

---

Need help? Check the documentation:
- `QUICK_START_MEMORY.md` - Quick reference
- `ADVANCED_MEMORY_SYSTEM.md` - Full architecture
- `MEMORY_FEATURE.md` - Technical details
