"""
Test script for Advanced Multi-Tier Memory System
Run this to verify all memory tiers are working correctly.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_imports():
    """Test if all dependencies are available."""
    print("\n" + "="*60)
    print("🔍 Testing Dependencies")
    print("="*60 + "\n")
    
    results = {}
    
    # Test Redis
    try:
        import redis
        results['redis'] = '✅ Available'
    except ImportError:
        results['redis'] = '❌ Not installed (pip install redis)'
    
    # Test PostgreSQL
    try:
        import psycopg2
        results['psycopg2'] = '✅ Available'
    except ImportError:
        results['psycopg2'] = '❌ Not installed (pip install psycopg2-binary)'
    
    # Test Qdrant
    try:
        from qdrant_client import QdrantClient
        results['qdrant'] = '✅ Available'
    except ImportError:
        results['qdrant'] = '❌ Not installed (pip install qdrant-client)'
    
    # Test Embeddings
    try:
        from sentence_transformers import SentenceTransformer
        results['embeddings'] = '✅ Available'
    except ImportError:
        results['embeddings'] = '❌ Not installed (pip install sentence-transformers)'
    
    # Test Core
    try:
        from memory_system import MemoryRouter
        results['memory_system'] = '✅ Available'
    except ImportError as e:
        results['memory_system'] = f'❌ Import failed: {e}'
    
    for package, status in results.items():
        print(f"{package:20s} {status}")
    
    return all('✅' in status for status in results.values())

def test_memory_router():
    """Test Memory Router initialization."""
    print("\n" + "="*60)
    print("🧠 Testing Memory Router")
    print("="*60 + "\n")
    
    try:
        from memory_system import MemoryRouter
        
        memory = MemoryRouter(
            student_id="test_student_001",
            session_id="test_session_001"
        )
        
        print("✅ Memory Router initialized successfully")
        print(f"   - Student ID: {memory.student_id}")
        print(f"   - Session ID: {memory.session_id}")
        
        return memory
    except Exception as e:
        print(f"❌ Memory Router initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_working_memory(memory):
    """Test Working Memory (Redis)."""
    print("\n" + "="*60)
    print("⚡ Testing Working Memory (Redis)")
    print("="*60 + "\n")
    
    try:
        wm = memory.working_memory
        
        # Add messages
        now = datetime.now()
        wm.add_message("user", "What is photosynthesis?", now)
        wm.add_message("assistant", "Photosynthesis is how plants make food!", now)
        
        # Retrieve messages
        messages = wm.get_recent_messages(limit=10)
        
        print(f"✅ Working Memory operational")
        print(f"   - Backend: {wm.backend}")
        print(f"   - Messages stored: {len(messages)}")
        
        for msg in messages:
            print(f"   - {msg['role']}: {msg['content'][:50]}...")
        
        return True
    except Exception as e:
        print(f"❌ Working Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_semantic_memory(memory):
    """Test Semantic Memory (PostgreSQL)."""
    print("\n" + "="*60)
    print("📚 Testing Semantic Memory (PostgreSQL)")
    print("="*60 + "\n")
    
    try:
        sm = memory.semantic_memory
        
        # Store facts
        now = datetime.now()
        facts = [
            "The Earth orbits the Sun",
            "Water boils at 100 degrees Celsius",
            "Jupiter is the largest planet"
        ]
        
        for fact in facts:
            sm.store_fact(fact, now, topic="science")
        
        # Retrieve facts
        retrieved = sm.retrieve_facts("planet", limit=5)
        
        print(f"✅ Semantic Memory operational")
        print(f"   - Backend: {sm.backend}")
        print(f"   - Facts stored: {len(facts)}")
        print(f"   - Facts retrieved: {len(retrieved)}")
        
        for fact in retrieved[:3]:
            print(f"   - {fact.get('fact', 'N/A')[:60]}...")
        
        return True
    except Exception as e:
        print(f"❌ Semantic Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_episodic_memory(memory):
    """Test Episodic Memory (Qdrant)."""
    print("\n" + "="*60)
    print("🎬 Testing Episodic Memory (Qdrant)")
    print("="*60 + "\n")
    
    try:
        em = memory.episodic_memory
        
        # Store interactions
        now = datetime.now()
        interactions = [
            ("What is gravity?", "Gravity pulls things together"),
            ("How do birds fly?", "Birds use wings and air currents"),
            ("Why is the sky blue?", "Light scatters in the atmosphere")
        ]
        
        for user_msg, assistant_msg in interactions:
            em.store_interaction(user_msg, assistant_msg, now)
        
        # Find similar
        similar = em.find_similar_sessions("Tell me about gravity", limit=3)
        
        print(f"✅ Episodic Memory operational")
        print(f"   - Backend: {em.backend}")
        print(f"   - Interactions stored: {len(interactions)}")
        print(f"   - Similar sessions found: {len(similar)}")
        
        for session in similar[:2]:
            print(f"   - Q: {session.get('user_message', 'N/A')[:40]}...")
        
        return True
    except Exception as e:
        print(f"❌ Episodic Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_knowledge_memory(memory):
    """Test Knowledge Memory (Qdrant)."""
    print("\n" + "="*60)
    print("🎓 Testing Knowledge Memory (Qdrant)")
    print("="*60 + "\n")
    
    try:
        km = memory.knowledge_memory
        
        # Store concepts
        now = datetime.now()
        concepts = [
            ("Photosynthesis", "Process plants use to make food", "Biology"),
            ("Gravity", "Force that attracts objects", "Physics"),
            ("Democracy", "Government by the people", "Social Studies")
        ]
        
        for concept, definition, category in concepts:
            km.store_concept(concept, now, definition, category)
        
        # Retrieve concepts
        retrieved = km.retrieve_concepts("science", limit=5)
        
        print(f"✅ Knowledge Memory operational")
        print(f"   - Backend: {km.backend}")
        print(f"   - Concepts stored: {len(concepts)}")
        print(f"   - Concepts retrieved: {len(retrieved)}")
        
        for concept in retrieved[:3]:
            print(f"   - {concept.get('concept', 'N/A')}: {concept.get('definition', 'N/A')[:40]}...")
        
        return True
    except Exception as e:
        print(f"❌ Knowledge Memory test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_context_building(memory):
    """Test unified context building."""
    print("\n" + "="*60)
    print("🔨 Testing Context Building")
    print("="*60 + "\n")
    
    try:
        query = "Tell me about planets"
        context = memory.build_context(query)
        
        print(f"✅ Context building successful")
        print(f"   - Query: {query}")
        print(f"   - Working memory items: {len(context.get('working', []))}")
        print(f"   - Semantic facts: {len(context.get('semantic', []))}")
        print(f"   - Episodic sessions: {len(context.get('episodic', []))}")
        print(f"   - Knowledge concepts: {len(context.get('knowledge', []))}")
        print(f"   - Summary: {context.get('summary', 'N/A')[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ Context building failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_memory_updates(memory):
    """Test memory update flow."""
    print("\n" + "="*60)
    print("🔄 Testing Memory Updates")
    print("="*60 + "\n")
    
    try:
        user_msg = "What causes rain?"
        assistant_msg = "Rain forms when water vapor in clouds condenses into droplets!"
        metadata = {"topic": "weather", "confidence": 0.95}
        
        memory.update_memories(user_msg, assistant_msg, metadata)
        
        print(f"✅ Memory updates successful")
        print(f"   - User message: {user_msg}")
        print(f"   - Assistant response: {assistant_msg[:50]}...")
        print(f"   - All memory tiers updated")
        
        return True
    except Exception as e:
        print(f"❌ Memory update failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_service_connections():
    """Test connections to all services."""
    print("\n" + "="*60)
    print("🔌 Testing Service Connections")
    print("="*60 + "\n")
    
    results = {}
    
    # Test Redis
    try:
        import redis
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        r.ping()
        results['Redis'] = '✅ Connected'
    except Exception as e:
        results['Redis'] = f'❌ Failed: {str(e)[:50]}'
    
    # Test PostgreSQL
    try:
        import psycopg2
        db_url = os.environ.get("DATABASE_URL", "postgresql://localhost/mimidb")
        conn = psycopg2.connect(db_url)
        conn.close()
        results['PostgreSQL'] = '✅ Connected'
    except Exception as e:
        results['PostgreSQL'] = f'❌ Failed: {str(e)[:50]}'
    
    # Test Qdrant
    try:
        from qdrant_client import QdrantClient
        qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
        client = QdrantClient(url=qdrant_url)
        client.get_collections()
        results['Qdrant'] = '✅ Connected'
    except Exception as e:
        results['Qdrant'] = f'❌ Failed: {str(e)[:50]}'
    
    for service, status in results.items():
        print(f"{service:15s} {status}")
    
    return results

def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("🧪 ADVANCED MEMORY SYSTEM TEST SUITE")
    print("="*60)
    
    # Check environment
    print(f"\n📋 Environment:")
    print(f"   - USE_ADVANCED_MEMORY: {os.environ.get('USE_ADVANCED_MEMORY', 'not set')}")
    print(f"   - REDIS_URL: {'set' if os.environ.get('REDIS_URL') else 'not set'}")
    print(f"   - DATABASE_URL: {'set' if os.environ.get('DATABASE_URL') else 'not set'}")
    print(f"   - QDRANT_URL: {'set' if os.environ.get('QDRANT_URL') else 'not set'}")
    
    # Test imports
    if not test_imports():
        print("\n⚠️  Some dependencies are missing. Install with:")
        print("   pip install -r requirements_advanced_memory.txt")
        print("\nContinuing with available components...\n")
    
    # Test service connections
    service_status = test_service_connections()
    
    # Test memory system
    try:
        memory = test_memory_router()
        if not memory:
            print("\n❌ Cannot continue - Memory Router failed to initialize")
            return
        
        # Run component tests
        tests = [
            ("Working Memory", lambda: test_working_memory(memory)),
            ("Semantic Memory", lambda: test_semantic_memory(memory)),
            ("Episodic Memory", lambda: test_episodic_memory(memory)),
            ("Knowledge Memory", lambda: test_knowledge_memory(memory)),
            ("Context Building", lambda: test_context_building(memory)),
            ("Memory Updates", lambda: test_memory_updates(memory)),
        ]
        
        results = {}
        for test_name, test_func in tests:
            try:
                results[test_name] = test_func()
            except Exception as e:
                results[test_name] = False
                print(f"\n❌ {test_name} test crashed: {e}")
        
        # Summary
        print("\n" + "="*60)
        print("📊 TEST SUMMARY")
        print("="*60 + "\n")
        
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:20s} {status}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n🎉 All tests passed! Advanced memory system is fully operational.")
        elif passed > 0:
            print("\n⚠️  Some tests failed. System will use fallbacks for failed components.")
        else:
            print("\n❌ All tests failed. Check service connections and dependencies.")
        
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
