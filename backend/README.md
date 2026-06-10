# mimi_smart_learning_tool

## 🧠 NEW: Advanced Multi-Tier Memory System

Mimi now has a **sophisticated 4-tier memory architecture** inspired by human cognition! Choose between basic conversation memory or advanced multi-tier memory with Redis, PostgreSQL, and Qdrant.

### Memory Architectures

#### 🎯 Basic Memory (Default - No Setup Required)
- ✅ Conversation history (MongoDB)
- ✅ Context-aware responses
- ✅ Session persistence
- ✅ Zero configuration

#### 🚀 Advanced Memory (Optional - Production Grade)
- ✅ **Working Memory** (Redis) - Current conversation, instant access
- ✅ **Semantic Memory** (PostgreSQL) - Structured facts and knowledge
- ✅ **Episodic Memory** (Qdrant) - Past experiences, vector similarity
- ✅ **Knowledge Memory** (Qdrant) - Long-term concepts and relationships
- ✅ Unified context building from all memory tiers
- ✅ Automatic fact extraction and concept learning
- ✅ Graceful fallbacks if services unavailable

### Quick Start

#### Basic Memory (Recommended for Getting Started)
No additional setup needed! Just start using:
```python
session.process_text("What is the solar system?")
session.process_text("Tell me about the biggest planet")
# ✅ LLM remembers we're discussing solar system!
```

#### Advanced Memory (For Production)
1. Install dependencies:
```bash
pip install -r requirements_advanced_memory.txt
```

2. Setup services (Docker):
```bash
# Redis (Working Memory)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# PostgreSQL (Semantic Memory)
docker run -d --name postgres -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:15-alpine

# Qdrant (Episodic & Knowledge Memory)
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant
```

3. Enable in `.env`:
```bash
USE_ADVANCED_MEMORY=true
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://postgres:pass@localhost/mimidb
QDRANT_URL=http://localhost:6333
```

4. Test:
```bash
python test_advanced_memory.py
```

### Documentation
- 📖 **[Basic Memory Guide](QUICK_START_MEMORY.md)** - Simple conversation memory
- 🧠 **[Advanced Memory System](ADVANCED_MEMORY_SYSTEM.md)** - Multi-tier architecture
- 📋 **[Implementation Details](MEMORY_FEATURE.md)** - Technical documentation
- 🧪 **[Test Scripts](test_memory.py)** - Verify installation

### Features Comparison

| Feature | Basic Memory | Advanced Memory |
|---------|--------------|-----------------|
| Conversation history | ✅ | ✅ |
| Follow-up questions | ✅ | ✅ |
| Session persistence | ✅ | ✅ |
| Fast access (Redis) | ❌ | ✅ |
| Fact extraction | ❌ | ✅ |
| Similar session search | ❌ | ✅ |
| Concept learning | ❌ | ✅ |
| Knowledge graphs | ❌ | ✅ |
| Setup complexity | None | Moderate |
| Infrastructure cost | Free | ~$5-20/month |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                       User Query                            │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────▼───────────┐
                │   Memory Router       │
                └───────────┬───────────┘
                            │
        ┌───────┬───────────┼───────────┬───────┐
        │       │           │           │       │
        ▼       ▼           ▼           ▼       ▼
    ┌──────┐┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐
    │Working││Semantic││Episodic││Knowledge││Context│
    │Memory ││Memory  ││Memory  ││Memory   ││Builder│
    │Redis  ││Postgres││Qdrant  ││Qdrant   ││       │
    └──────┘└──────┘  └──────┘  └──────┘  └──────┘
        │       │           │           │       │
        └───────┴───────────┴───────────┴───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │     LLM       │
                    └───────────────┘
```

---