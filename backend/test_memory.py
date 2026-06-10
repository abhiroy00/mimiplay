"""
Test script for LLM conversation memory feature.
Run this to verify memory is working correctly.
"""

import os
import logging
from mimi_llm_session import MimiLLMSession
from dotenv import load_dotenv

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO)

def test_memory():
    """Test conversation memory with a series of related questions."""
    
    print("\n" + "="*60)
    print("🧠 Testing LLM Conversation Memory")
    print("="*60 + "\n")
    
    # Create a test session
    session = MimiLLMSession(
        student_name="Test Student",
        session_id="test_memory_session_001",
        student_age=10
    )
    
    # Test conversation flow
    test_questions = [
        "What is the solar system?",
        "How many planets are there?",
        "Tell me more about the biggest one",  # Should reference Jupiter without being told
        "What about the smallest?",  # Should reference planets from context
    ]
    
    print("Starting conversation test...\n")
    
    for i, question in enumerate(test_questions, 1):
        print(f"Question {i}: {question}")
        print("-" * 60)
        
        try:
            result = session.process_text(question)
            answer = result.get("text", "No response")
            print(f"Mimi: {answer}\n")
            
            # Show memory stats
            stats = session.get_memory_stats()
            print(f"💾 Memory: {stats['messages_in_memory']} messages in history")
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}\n")
    
    # Test memory stats
    print("="*60)
    print("📊 Final Memory Statistics")
    print("="*60)
    stats = session.get_memory_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test memory clear
    print("\n" + "="*60)
    print("🧹 Testing Memory Clear")
    print("="*60)
    session.clear_memory()
    stats = session.get_memory_stats()
    print(f"  Messages after clear: {stats['messages_in_memory']}")
    
    print("\n✅ Memory test completed!\n")


def test_persistence():
    """Test that memory persists across session instances."""
    
    print("\n" + "="*60)
    print("💾 Testing Memory Persistence")
    print("="*60 + "\n")
    
    session_id = "test_persistence_session"
    
    # First session
    print("Creating first session...")
    session1 = MimiLLMSession(
        student_name="Test Student",
        session_id=session_id,
        student_age=10
    )
    
    session1.process_text("What is gravity?")
    stats1 = session1.get_memory_stats()
    print(f"Session 1 memory: {stats1['messages_in_memory']} messages\n")
    
    # Simulate session restart (new instance with same session_id)
    print("Creating new session with same session_id...")
    session2 = MimiLLMSession(
        student_name="Test Student",
        session_id=session_id,
        student_age=10
    )
    
    # This should load previous conversation from database
    session2.process_text("Can you explain more?")
    stats2 = session2.get_memory_stats()
    print(f"Session 2 memory: {stats2['messages_in_memory']} messages")
    
    if stats2['messages_in_memory'] > 0:
        print("✅ Memory successfully loaded from database!")
    else:
        print("⚠️  Memory not loaded - check database connection")
    
    print()


if __name__ == "__main__":
    # Check for API keys
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Error: No API keys found!")
        print("Please set OPENAI_API_KEY or ANTHROPIC_API_KEY in your .env file")
        exit(1)
    
    # Run tests
    try:
        test_memory()
        test_persistence()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
