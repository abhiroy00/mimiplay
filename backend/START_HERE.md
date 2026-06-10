# 🚀 START HERE - Complete Setup Guide

Welcome! This guide will help you set up and test the Mimi AI memory system in **under 15 minutes**.

## ⚡ Quick Setup (Choose One)

### Option A: Automated Setup (Easiest)
```bash
python quick_start.py
```
This interactive script will:
- ✅ Create your .env file
- ✅ Install dependencies
- ✅ Test configuration
- ✅ Guide you through next steps

### Option B: Manual Setup (Step by Step)
Follow the instructions below.

---

## 📋 Manual Setup Steps

### Step 1: Create Configuration File (2 minutes)

1. Copy the example file:
```bash
copy .env.example .env
```

2. Edit `.env` and fill in:

```bash
# Required: MongoDB connection
MONGODB_URI=mongodb://localhost:27017/
# Or use MongoDB Atlas: mongodb+srv://username:password@cluster.mongodb.net/

# Required: At least one API key
OPENAI_API_KEY=sk-your-openai-key-here

# Required: Secret for JWT
SECRET=change-this-to-random-string

# Memory setting (keep as false for now)
USE_ADVANCED_MEMORY=false
```

**Get API Keys:**
- OpenAI: https://platform.openai.com/api-keys
- MongoDB Atlas (free): https://www.mongodb.com/cloud/atlas

### Step 2: Install Dependencies (3 minutes)

```bash
# Install Python packages
pip install -r requirements.txt
```

### Step 3: Test Configuration (2 minutes)

```bash
# Test your setup
python test_api.py
```

**Expected output:**
```
✅ MongoDB Connection        PASS
✅ LLM API Keys             PASS
✅ API Health               PASS
✅ Session Start            PASS
```

### Step 4: Test Memory System (3 minutes)

```bash
# Test that memory works
python test_live_memory.py
```

**What you should see:**
- Multiple Q&A turns
- LLM remembering context from previous questions
- Memory statistics increasing

### Step 5: Start the Application (1 minute)

```bash
# Start Flask app
python app.py
```

**Expected output:**
```
[INFO] MimiLLMSession: OpenAI=True, Memory=basic
 * Running on http://127.0.0.1:5000
```

---

## ✅ Verification Checklist

After setup, verify everything works:

- [ ] `.env` file created with your API keys
- [ ] `python test_api.py` - All tests pass
- [ ] `python test_live_memory.py` - Shows contextual responses
- [ ] `python app.py` - Server starts without errors
- [ ] Memory mode shows as "basic"

---

## 🎯 What You Have Now

### ✅ Basic Memory System (Working!)

Your LLM now has:
- ✅ Conversation history (last 20 messages)
- ✅ Context-aware responses
- ✅ Session persistence in MongoDB
- ✅ Works with OpenAI & Anthropic

**Example conversation:**
```
You: "What is the solar system?"
Mimi: "The solar system is our Sun and 8 planets..."

You: "Tell me about the biggest one"
Mimi: "Jupiter is the largest planet!" ✅ Remembers context!
```

---

## 🚀 Optional: Advanced Memory Setup

Want the full 4-tier memory system? Follow these extra steps:

### Requirements
- Docker Desktop installed
- Additional 15-30 minutes

### Steps

1. **Install advanced dependencies:**
```bash
pip install -r requirements_advanced_memory.txt
```

2. **Start Docker services:**
```bash
# Redis (Working Memory)
docker run -d --name mimi-redis -p 6379:6379 redis:7-alpine

# PostgreSQL (Semantic Memory)
docker run -d --name mimi-postgres -e POSTGRES_PASSWORD=mimipass -e POSTGRES_DB=mimidb -p 5432:5432 postgres:15-alpine

# Qdrant (Episodic & Knowledge Memory)
docker run -d --name mimi-qdrant -p 6333:6333 qdrant/qdrant
```

3. **Update .env file:**
```bash
USE_ADVANCED_MEMORY=true
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://postgres:mimipass@localhost:5432/mimidb
QDRANT_URL=http://localhost:6333
```

4. **Test advanced memory:**
```bash
python test_advanced_memory.py
```

5. **Restart app:**
```bash
python app.py
# Should now show: Memory=advanced
```

---

## 📚 Documentation Files

### Getting Started
- **START_HERE.md** (this file) - Quick setup
- **SETUP_GUIDE.md** - Detailed step-by-step guide
- **QUICK_START_MEMORY.md** - Developer quick reference

### Features
- **MEMORY_FEATURE.md** - Basic memory technical details
- **ADVANCED_MEMORY_SYSTEM.md** - Advanced 4-tier system
- **MEMORY_IMPLEMENTATION_COMPLETE.md** - Complete overview

### Testing & Deployment
- **test_api.py** - Test API configuration
- **test_memory.py** - Test basic memory
- **test_live_memory.py** - Test with real conversations
- **test_advanced_memory.py** - Test 4-tier system
- **DEPLOYMENT_CHECKLIST.md** - Production deployment

---

## 🧪 Test Scripts Reference

### test_api.py
Tests your basic setup:
```bash
python test_api.py
```
Checks: MongoDB, API keys, server health

### test_memory.py
Tests basic memory functionality:
```bash
python test_memory.py
```
Tests: Conversation history, persistence

### test_live_memory.py
Tests memory with real API calls:
```bash
python test_live_memory.py
```
Tests: Context awareness, multi-turn conversations

### test_advanced_memory.py
Tests 4-tier advanced system:
```bash
python test_advanced_memory.py
```
Tests: Redis, PostgreSQL, Qdrant, all memory tiers

---

## 🐛 Troubleshooting

### Issue: "Module not found"
```bash
# Solution: Reinstall dependencies
pip install -r requirements.txt
```

### Issue: "MongoDB connection failed"
```bash
# Solution 1: Start local MongoDB
net start MongoDB

# Solution 2: Use MongoDB Atlas (cloud)
# Update MONGODB_URI in .env with Atlas connection string
```

### Issue: "OpenAI API key invalid"
```bash
# Solution:
# 1. Check .env file has correct key
# 2. Verify key at: https://platform.openai.com/api-keys
# 3. Make sure key starts with sk-
```

### Issue: "Authentication failed"
```bash
# Solution:
# Check SECRET is set in .env file
# For testing, you can temporarily disable auth in app.py
```

### Issue: "Docker containers won't start"
```bash
# Solution: Remove and recreate
docker rm -f mimi-redis mimi-postgres mimi-qdrant
# Then run docker commands again
```

---

## 🎓 Understanding Memory Systems

### Basic Memory (Default)
```
User → MongoDB → LLM → Response
         ↓
    (stores history)
```
- Simple, reliable
- Zero additional setup
- Perfect for getting started

### Advanced Memory (Optional)
```
User → Memory Router → [4 Memory Tiers] → LLM → Response
                         ↓    ↓    ↓   ↓
                       Redis PG Qdrant Qdrant
```
- Production-grade
- Human-like memory
- Requires Docker services

---

## ⚡ Quick Commands

### Start everything:
```bash
python app.py
```

### Test everything:
```bash
python test_api.py           # Configuration test
python test_live_memory.py   # Memory test
```

### Stop everything:
```bash
Ctrl+C                       # Stop Flask
docker stop mimi-redis mimi-postgres mimi-qdrant  # Stop Docker
```

---

## 🎯 Next Steps

Once everything is working:

1. **Integrate with your frontend**
   - Use endpoints: `/start-mimi-session`, `/mimi-chat-audio`
   - Memory works automatically

2. **Test with real students**
   - Monitor conversation quality
   - Check memory is being used correctly

3. **Consider advanced memory**
   - When you need better context awareness
   - For production deployment

4. **Read documentation**
   - Learn about all features
   - Understand architecture

---

## 💬 Support & Resources

### Documentation
- All `.md` files in project root
- Inline code comments
- Test script examples

### API Endpoints
- `POST /start-mimi-session` - Start conversation
- `POST /mimi-chat-audio` - Send audio message
- `GET /mimi-get` - Get response
- `POST /mimi-save-chat` - Save message (auto)

### Environment Variables
```bash
MONGODB_URI          # Database connection
OPENAI_API_KEY       # LLM provider
SECRET               # JWT secret
USE_ADVANCED_MEMORY  # Memory mode (true/false)
```

---

## ✨ Summary

🎉 **You now have a working AI tutoring system with memory!**

What works:
- ✅ Conversation memory
- ✅ Context-aware responses  
- ✅ Session persistence
- ✅ Multi-turn dialogues
- ✅ Student profiles

Start with basic memory, upgrade to advanced when ready!

---

**Ready to begin? Run:**
```bash
python quick_start.py
```

Or jump straight to:
```bash
python test_live_memory.py
```

Good luck! 🚀
