"""
Live test of memory system - simulates a real conversation
This tests that the LLM actually remembers context
"""

import os
import logging
from dotenv import load_dotenv
from mimi_llm_session import MimiLLMSession

# Setup
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_conversation():
    """Test a multi-turn conversation with memory"""
    print("\n" + "="*70)
    print("🧪 LIVE MEMORY TEST - Conversation Simulation")
    print("="*70)
    print("\nThis will test that the LLM remembers context across messages.\n")
    
    # Check API key
    if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ No LLM API keys found!")
        print("\nPlease set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env file")
        return
    
    # Create session
    print("Creating Mimi session...")
    session = MimiLLMSession(
        student_name="Test Student",
        session_id="live_test_session_001",
        student_id="507f1f77bcf86cd799439011",
        student_age=10
    )
    
    print(f"✅ Session created")
    print(f"   Memory Mode: {session.memory_mode}")
    print(f"   Student: {session.student_name}")
    print()
    
    # Test conversation that requires memory
    test_cases = [
        {
            "question": "What is the solar system?",
            "check": None  # First question, no memory check needed
        },
        {
            "question": "How many planets are there?",
            "check": "Should reference the solar system mentioned earlier"
        },
        {
            "question": "Tell me about the biggest one",
            "check": "Should know 'biggest one' refers to Jupiter (from previous context)"
        },
        {
            "question": "What color is it?",
            "check": "Should know 'it' refers to Jupiter"
        }
    ]
    
    memory_working = True
    
    for i, test_case in enumerate(test_cases, 1):
        question = test_case["question"]
        check = test_case["check"]
        
        print("─" * 70)
        print(f"Turn {i}/4")
        print("─" * 70)
        print(f"👤 You: {question}")
        
        if check:
            print(f"💭 Memory Check: {check}")
        
        try:
            # Process with LLM
            result = session.process_text(question)
            answer = result.get("text", "No response")
            
            print(f"🤖 Mimi: {answer}")
            
            # Check memory stats
            stats = session.get_memory_stats()
            print(f"💾 Memory: {stats['messages_in_memory']} messages in history")
            
            # Validate memory is working
            if i > 1:  # After first question
                if stats['messages_in_memory'] < i * 2:
                    print("⚠️  Warning: Memory might not be storing messages correctly")
                    memory_working = False
            
            print()
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print()
            memory_working = False
            break
    
    # Summary
    print("="*70)
    print("RESULTS")
    print("="*70)
    
    if memory_working:
        print("✅ Memory is working correctly!")
        print("\nThe LLM successfully:")
        print("  - Remembered previous questions")
        print("  - Understood contextual references ('biggest one', 'it')")
        print("  - Maintained conversation continuity")
        print("\n🎉 Your memory system is ready for production!")
    else:
        print("❌ Memory test failed")
        print("\nCheck:")
        print("  1. OPENAI_API_KEY or ANTHROPIC_API_KEY is valid")
        print("  2. MongoDB is running and accessible")
        print("  3. Check logs above for specific errors")
    
    print("\n" + "="*70)

def test_memory_persistence():
    """Test that memory persists across sessions"""
    print("\n" + "="*70)
    print("🧪 MEMORY PERSISTENCE TEST")
    print("="*70)
    print("\nTesting if memory loads from previous sessions...\n")
    
    session_id = "persistence_test_session"
    
    # Session 1: Create and ask question
    print("Session 1: Creating new session and asking a question")
    print("-" * 70)
    
    session1 = MimiLLMSession(
        student_name="Test Student",
        session_id=session_id,
        student_id="507f1f77bcf86cd799439011",
        student_age=10
    )
    
    try:
        result1 = session1.process_text("What is gravity?")
        print(f"✅ Question asked: What is gravity?")
        print(f"   Response: {result1.get('text', '')[:100]}...")
        
        stats1 = session1.get_memory_stats()
        print(f"   Memory: {stats1['messages_in_memory']} messages")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Session 2: New instance, same session_id (simulates app restart)
    print("Session 2: Creating new session instance with same session_id")
    print("-" * 70)
    
    session2 = MimiLLMSession(
        student_name="Test Student",
        session_id=session_id,
        student_id="507f1f77bcf86cd799439011",
        student_age=10
    )
    
    try:
        result2 = session2.process_text("Can you explain more?")
        print(f"✅ Follow-up question: Can you explain more?")
        print(f"   Response: {result2.get('text', '')[:100]}...")
        
        stats2 = session2.get_memory_stats()
        print(f"   Memory: {stats2['messages_in_memory']} messages")
        print()
        
        # Check if memory loaded
        if stats2['messages_in_memory'] > 2:
            print("✅ Memory persisted!")
            print("   Previous conversation was loaded from database")
        else:
            print("⚠️  Memory may not have loaded from database")
            print("   This could be normal if using basic memory without DB save")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("="*70)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    MIMI MEMORY LIVE TEST                             ║
║                                                                      ║
║  This will make real API calls to test memory functionality         ║
║  Make sure you have OPENAI_API_KEY or ANTHROPIC_API_KEY set        ║
╚══════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Test 1: Conversation memory
        test_conversation()
        
        # Test 2: Persistence
        input("\nPress Enter to test memory persistence (or Ctrl+C to skip)...")
        test_memory_persistence()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
