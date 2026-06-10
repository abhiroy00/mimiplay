"""
Advanced Multi-Tiered Memory System for Mimi LLM

Architecture:
- Working Memory: Current conversation (Redis - fast access)
- Semantic Memory: Facts and knowledge (PostgreSQL - structured data)
- Episodic Memory: Past experiences (Qdrant - vector similarity)
- Knowledge Memory: Long-term learning (Qdrant - embeddings)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
import hashlib

logger = logging.getLogger(__name__)

# Optional imports - gracefully handle missing dependencies
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available - working memory will use in-memory fallback")

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    logger.warning("PostgreSQL not available - semantic memory will use MongoDB fallback")

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("Qdrant not available - episodic/knowledge memory will use basic similarity")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available - will use OpenAI embeddings")

from pymongo import MongoClient


class MemoryRouter:
    """
    Routes queries to appropriate memory stores and builds unified context.
    """
    
    def __init__(self, student_id: str, session_id: str):
        self.student_id = student_id
        self.session_id = session_id
        
        # Initialize all memory tiers
        self.working_memory = WorkingMemory(session_id)
        self.semantic_memory = SemanticMemory(student_id)
        self.episodic_memory = EpisodicMemory(student_id)
        self.knowledge_memory = KnowledgeMemory(student_id)
        
        logger.info(f"[MemoryRouter] Initialized for student={student_id}, session={session_id}")
    
    def build_context(self, user_query: str, max_tokens: int = 2000) -> Dict[str, Any]:
        """
        Build comprehensive context from all memory tiers for LLM.
        
        Returns:
            {
                "working": [...],      # Recent conversation
                "semantic": [...],     # Relevant facts
                "episodic": [...],     # Similar past experiences
                "knowledge": [...],    # Related learned concepts
                "summary": "..."       # Unified summary
            }
        """
        logger.info(f"[MemoryRouter] Building context for query: {user_query[:100]}")
        
        # Fetch from all memory tiers in parallel (could be optimized)
        working_context = self.working_memory.get_recent_messages(limit=10)
        semantic_context = self.semantic_memory.retrieve_facts(user_query, limit=5)
        episodic_context = self.episodic_memory.find_similar_sessions(user_query, limit=3)
        knowledge_context = self.knowledge_memory.retrieve_concepts(user_query, limit=5)
        
        context = {
            "working": working_context,
            "semantic": semantic_context,
            "episodic": episodic_context,
            "knowledge": knowledge_context,
            "summary": self._build_summary(
                working_context, 
                semantic_context, 
                episodic_context, 
                knowledge_context
            )
        }
        
        logger.info(f"[MemoryRouter] Context built: working={len(working_context)}, "
                   f"semantic={len(semantic_context)}, episodic={len(episodic_context)}, "
                   f"knowledge={len(knowledge_context)}")
        
        return context
    
    def _build_summary(self, working, semantic, episodic, knowledge) -> str:
        """Create a unified context summary for LLM."""
        parts = []
        
        if working:
            parts.append(f"Recent conversation: {len(working)} messages")
        if semantic:
            parts.append(f"Known facts: {', '.join([f['fact'][:50] for f in semantic[:2]])}")
        if episodic:
            parts.append(f"Similar past sessions: {len(episodic)}")
        if knowledge:
            parts.append(f"Related concepts: {', '.join([k['concept'][:30] for k in knowledge[:2]])}")
        
        return " | ".join(parts) if parts else "No prior context"
    
    def update_memories(self, user_message: str, assistant_response: str, metadata: Dict = None):
        """
        Update all memory tiers after an interaction.
        """
        timestamp = datetime.now()
        
        # Update working memory (conversation)
        self.working_memory.add_message("user", user_message, timestamp)
        self.working_memory.add_message("assistant", assistant_response, timestamp)
        
        # Extract and store facts in semantic memory
        facts = self._extract_facts(user_message, assistant_response)
        for fact in facts:
            self.semantic_memory.store_fact(fact, timestamp)
        
        # Store session summary in episodic memory
        self.episodic_memory.store_interaction(user_message, assistant_response, timestamp, metadata)
        
        # Update knowledge base with learned concepts
        concepts = self._extract_concepts(user_message, assistant_response)
        for concept in concepts:
            self.knowledge_memory.store_concept(concept, timestamp)
        
        logger.info(f"[MemoryRouter] Updated all memory tiers")
    
    def _extract_facts(self, user_msg: str, assistant_msg: str) -> List[str]:
        """Extract factual statements from conversation."""
        # Simple keyword-based extraction (can be improved with NLP)
        facts = []
        triggers = ["is", "are", "was", "were", "has", "have", "can", "will"]
        
        for sentence in assistant_msg.split(". "):
            if any(trigger in sentence.lower() for trigger in triggers):
                if len(sentence) > 20 and len(sentence) < 200:
                    facts.append(sentence.strip())
        
        return facts[:3]  # Limit to top 3 facts
    
    def _extract_concepts(self, user_msg: str, assistant_msg: str) -> List[str]:
        """Extract key concepts from conversation."""
        # Simple noun extraction (can be improved with NLP)
        # For now, extract capitalized words as potential concepts
        import re
        concepts = set()
        
        text = user_msg + " " + assistant_msg
        # Find capitalized words that aren't sentence starts
        words = re.findall(r'\b[A-Z][a-z]+\b', text)
        
        for word in words:
            if len(word) > 3:  # Filter short words
                concepts.add(word)
        
        return list(concepts)[:5]  # Limit to top 5


class WorkingMemory:
    """
    Short-term conversation memory using Redis (or in-memory fallback).
    TTL: 1 hour (expires after session ends)
    """
    
    def __init__(self, session_id: str, ttl_seconds: int = 3600):
        self.session_id = session_id
        self.ttl = ttl_seconds
        
        if REDIS_AVAILABLE:
            redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
            try:
                self.redis = redis.from_url(redis_url, decode_responses=True)
                self.redis.ping()  # Test connection
                self.backend = "redis"
                logger.info("[WorkingMemory] Using Redis backend")
            except Exception as e:
                logger.warning(f"[WorkingMemory] Redis connection failed: {e}, using in-memory")
                self.backend = "memory"
                self.memory_store = []
        else:
            self.backend = "memory"
            self.memory_store = []
            logger.info("[WorkingMemory] Using in-memory backend")
    
    def add_message(self, role: str, content: str, timestamp: datetime):
        """Add a message to working memory."""
        message = {
            "role": role,
            "content": content,
            "timestamp": timestamp.isoformat()
        }
        
        if self.backend == "redis":
            key = f"working_memory:{self.session_id}"
            self.redis.rpush(key, json.dumps(message))
            self.redis.expire(key, self.ttl)  # Reset TTL
        else:
            self.memory_store.append(message)
            # Keep only recent messages in memory
            if len(self.memory_store) > 50:
                self.memory_store = self.memory_store[-50:]
    
    def get_recent_messages(self, limit: int = 10) -> List[Dict]:
        """Retrieve recent messages from working memory."""
        if self.backend == "redis":
            key = f"working_memory:{self.session_id}"
            messages = self.redis.lrange(key, -limit, -1)
            return [json.loads(msg) for msg in messages]
        else:
            return self.memory_store[-limit:]
    
    def clear(self):
        """Clear working memory (e.g., when session ends)."""
        if self.backend == "redis":
            key = f"working_memory:{self.session_id}"
            self.redis.delete(key)
        else:
            self.memory_store = []


class SemanticMemory:
    """
    Structured facts and knowledge using PostgreSQL (or MongoDB fallback).
    Stores validated facts learned about topics.
    """
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        
        if POSTGRES_AVAILABLE:
            try:
                self.pg_conn = psycopg2.connect(
                    os.environ.get("DATABASE_URL", "postgresql://localhost/mimidb")
                )
                self._ensure_table()
                self.backend = "postgres"
                logger.info("[SemanticMemory] Using PostgreSQL backend")
            except Exception as e:
                logger.warning(f"[SemanticMemory] PostgreSQL failed: {e}, using MongoDB")
                self._init_mongo_fallback()
        else:
            self._init_mongo_fallback()
    
    def _init_mongo_fallback(self):
        """Initialize MongoDB as fallback for semantic memory."""
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        self.mongo_client = MongoClient(mongo_uri)
        self.collection = self.mongo_client["AlexiDB"]["semantic_memory"]
        self.backend = "mongo"
        logger.info("[SemanticMemory] Using MongoDB fallback")
    
    def _ensure_table(self):
        """Create PostgreSQL table if it doesn't exist."""
        with self.pg_conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id SERIAL PRIMARY KEY,
                    student_id VARCHAR(100),
                    fact TEXT NOT NULL,
                    topic VARCHAR(200),
                    confidence FLOAT DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP,
                    access_count INT DEFAULT 0
                )
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_student 
                ON semantic_memory(student_id)
            """)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_topic 
                ON semantic_memory(topic)
            """)
            self.pg_conn.commit()
    
    def store_fact(self, fact: str, timestamp: datetime, topic: str = None):
        """Store a factual statement."""
        if not topic:
            topic = self._extract_topic(fact)
        
        if self.backend == "postgres":
            with self.pg_conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO semantic_memory (student_id, fact, topic, created_at)
                    VALUES (%s, %s, %s, %s)
                """, (self.student_id, fact, topic, timestamp))
                self.pg_conn.commit()
        else:
            self.collection.insert_one({
                "student_id": self.student_id,
                "fact": fact,
                "topic": topic,
                "created_at": timestamp,
                "access_count": 0
            })
    
    def retrieve_facts(self, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve relevant facts based on query."""
        topic = self._extract_topic(query)
        
        if self.backend == "postgres":
            with self.pg_conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT fact, topic, confidence, created_at
                    FROM semantic_memory
                    WHERE student_id = %s AND topic ILIKE %s
                    ORDER BY confidence DESC, last_accessed DESC
                    LIMIT %s
                """, (self.student_id, f"%{topic}%", limit))
                
                # Update access stats
                cur.execute("""
                    UPDATE semantic_memory
                    SET last_accessed = CURRENT_TIMESTAMP, access_count = access_count + 1
                    WHERE student_id = %s AND topic ILIKE %s
                """, (self.student_id, f"%{topic}%"))
                self.pg_conn.commit()
                
                return [dict(row) for row in cur.fetchall()]
        else:
            facts = self.collection.find({
                "student_id": self.student_id,
                "topic": {"$regex": topic, "$options": "i"}
            }).sort("access_count", -1).limit(limit)
            
            # Update access count
            self.collection.update_many(
                {"student_id": self.student_id, "topic": {"$regex": topic, "$options": "i"}},
                {"$inc": {"access_count": 1}}
            )
            
            return list(facts)
    
    def _extract_topic(self, text: str) -> str:
        """Extract main topic from text (simple keyword extraction)."""
        # Remove common words
        common_words = {"what", "is", "the", "a", "an", "how", "why", "when", "where"}
        words = text.lower().split()
        keywords = [w for w in words if w not in common_words and len(w) > 3]
        return keywords[0] if keywords else "general"


class EpisodicMemory:
    """
    Past session experiences using Qdrant vector database.
    Stores embeddings of past conversations for similarity search.
    """
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.collection_name = "episodic_memory"
        
        if QDRANT_AVAILABLE and EMBEDDINGS_AVAILABLE:
            try:
                qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
                self.qdrant = QdrantClient(url=qdrant_url)
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                self._ensure_collection()
                self.backend = "qdrant"
                logger.info("[EpisodicMemory] Using Qdrant backend")
            except Exception as e:
                logger.warning(f"[EpisodicMemory] Qdrant failed: {e}, using fallback")
                self._init_fallback()
        else:
            self._init_fallback()
    
    def _init_fallback(self):
        """MongoDB fallback for episodic memory."""
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        self.mongo_client = MongoClient(mongo_uri)
        self.collection = self.mongo_client["AlexiDB"]["episodic_memory"]
        self.backend = "mongo"
        logger.info("[EpisodicMemory] Using MongoDB fallback")
    
    def _ensure_collection(self):
        """Create Qdrant collection if needed."""
        collections = self.qdrant.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
    
    def store_interaction(self, user_msg: str, assistant_msg: str, 
                         timestamp: datetime, metadata: Dict = None):
        """Store a conversation interaction."""
        text = f"User: {user_msg}\nAssistant: {assistant_msg}"
        
        if self.backend == "qdrant":
            # Generate embedding
            embedding = self.encoder.encode(text).tolist()
            
            # Generate unique ID
            point_id = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            
            # Store in Qdrant
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "student_id": self.student_id,
                        "user_message": user_msg,
                        "assistant_message": assistant_msg,
                        "timestamp": timestamp.isoformat(),
                        "metadata": metadata or {}
                    }
                )]
            )
        else:
            # Store in MongoDB
            self.collection.insert_one({
                "student_id": self.student_id,
                "user_message": user_msg,
                "assistant_message": assistant_msg,
                "timestamp": timestamp,
                "metadata": metadata or {},
                "text": text  # For basic text search
            })
    
    def find_similar_sessions(self, query: str, limit: int = 3) -> List[Dict]:
        """Find similar past interactions using vector similarity."""
        if self.backend == "qdrant":
            # Generate query embedding
            query_embedding = self.encoder.encode(query).tolist()
            
            # Search similar vectors
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[FieldCondition(key="student_id", match=MatchValue(value=self.student_id))]
                ),
                limit=limit
            )
            
            return [
                {
                    "user_message": r.payload["user_message"],
                    "assistant_message": r.payload["assistant_message"],
                    "timestamp": r.payload["timestamp"],
                    "similarity": r.score
                }
                for r in results
            ]
        else:
            # Simple text search fallback
            results = self.collection.find({
                "student_id": self.student_id,
                "text": {"$regex": query.split()[0], "$options": "i"}
            }).sort("timestamp", -1).limit(limit)
            
            return list(results)


class KnowledgeMemory:
    """
    Long-term conceptual knowledge using Qdrant.
    Stores learned concepts and their relationships.
    """
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.collection_name = "knowledge_memory"
        
        if QDRANT_AVAILABLE and EMBEDDINGS_AVAILABLE:
            try:
                qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
                self.qdrant = QdrantClient(url=qdrant_url)
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                self._ensure_collection()
                self.backend = "qdrant"
                logger.info("[KnowledgeMemory] Using Qdrant backend")
            except Exception as e:
                logger.warning(f"[KnowledgeMemory] Qdrant failed: {e}, using fallback")
                self._init_fallback()
        else:
            self._init_fallback()
    
    def _init_fallback(self):
        """MongoDB fallback."""
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        self.mongo_client = MongoClient(mongo_uri)
        self.collection = self.mongo_client["AlexiDB"]["knowledge_memory"]
        self.backend = "mongo"
        logger.info("[KnowledgeMemory] Using MongoDB fallback")
    
    def _ensure_collection(self):
        """Create Qdrant collection."""
        collections = self.qdrant.get_collections().collections
        if not any(c.name == self.collection_name for c in collections):
            self.qdrant.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=384, distance=Distance.COSINE)
            )
    
    def store_concept(self, concept: str, timestamp: datetime, 
                     definition: str = None, category: str = None):
        """Store a learned concept."""
        text = f"{concept}: {definition}" if definition else concept
        
        if self.backend == "qdrant":
            embedding = self.encoder.encode(text).tolist()
            point_id = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
            
            self.qdrant.upsert(
                collection_name=self.collection_name,
                points=[PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "student_id": self.student_id,
                        "concept": concept,
                        "definition": definition,
                        "category": category,
                        "timestamp": timestamp.isoformat(),
                        "access_count": 0
                    }
                )]
            )
        else:
            self.collection.update_one(
                {"student_id": self.student_id, "concept": concept},
                {"$set": {
                    "definition": definition,
                    "category": category,
                    "timestamp": timestamp
                }, "$inc": {"access_count": 1}},
                upsert=True
            )
    
    def retrieve_concepts(self, query: str, limit: int = 5) -> List[Dict]:
        """Retrieve related concepts."""
        if self.backend == "qdrant":
            query_embedding = self.encoder.encode(query).tolist()
            
            results = self.qdrant.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=Filter(
                    must=[FieldCondition(key="student_id", match=MatchValue(value=self.student_id))]
                ),
                limit=limit
            )
            
            return [
                {
                    "concept": r.payload["concept"],
                    "definition": r.payload.get("definition"),
                    "category": r.payload.get("category"),
                    "relevance": r.score
                }
                for r in results
            ]
        else:
            results = self.collection.find({
                "student_id": self.student_id
            }).sort("access_count", -1).limit(limit)
            
            return list(results)


# Utility functions
def get_memory_system(student_id: str, session_id: str) -> MemoryRouter:
    """
    Factory function to create a memory system for a student session.
    """
    return MemoryRouter(student_id, session_id)


if __name__ == "__main__":
    # Test the memory system
    logging.basicConfig(level=logging.INFO)
    
    memory = get_memory_system("test_student", "test_session")
    
    # Test building context
    context = memory.build_context("What is photosynthesis?")
    print(json.dumps(context, indent=2, default=str))
    
    # Test updating memories
    memory.update_memories(
        "What is photosynthesis?",
        "Photosynthesis is how plants make food using sunlight!"
    )
    
    print("✅ Memory system test complete")
