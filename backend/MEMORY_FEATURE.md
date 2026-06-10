# 🧠 LLM Conversation Memory Feature

## Overview
The Mimi LLM now has **conversation memory** that allows it to remember everything from previous messages in a conversation session. This creates a more natural, context-aware interaction where students can ask follow-up questions without repeating context.

## How It Works

### 1. **Automatic History Loading**
- When a conversation starts, the system automatically loads the last 20 messages from the database
- Messages are retrieved from the `mimi_chats` collection using the `session_id`
- Only recent messages are kept in memory to optimize performance and token usage

### 2. **Context-Aware Responses**
- Every time a student asks a question, the LLM receives:
  - System prompt (defines Mimi's personality and capabilities)
  - **Full conversation history** (previous questions and answers)
  - Current user message
  
- This allows natural conversations like:
  ```
  Student: "What is the solar system?"
  Mimi: "The solar system is our Sun and all the planets that orbit it. There are 8 planets including Earth!"
  
  Student: "Tell me more about the biggest one"
  Mimi: "Jupiter is the largest planet! It's so big that all other planets could fit inside it."
  ```

### 3. **Persistent Memory**
- Messages are stored in MongoDB (`mimi_chats` collection)
- Format:
  ```json
  {
    "session_id": "unique-session-id",
    "student_id": ObjectId,
    "student_name": "John",
    "messages": [
      {
        "role": "user",
        "message": "What is gravity?",
        "timestamp": "2024-01-15T10:30:00"
      },
      {
        "role": "assistant", 
        "message": "Gravity is a force that pulls things toward each other...",
        "timestamp": "2024-01-15T10:30:05"
      }
    ]
  }
  ```

### 4. **Memory Limits**
- **In-memory cache**: Last 20 messages (10 conversation turns)
- **Token optimization**: Only recent messages are sent to LLM to stay within limits
- **Automatic cleanup**: Old messages are trimmed to prevent memory bloat

## Configuration

### Adjusting Memory Size
Edit `mimi_llm_session.py`:
```python
self.max_history_messages = 20  # Change this number
```

**Guidelines:**
- **10-20 messages**: Good for short tutoring sessions
- **20-40 messages**: Better for extended learning sessions
- **40+ messages**: May hit token limits with verbose responses

### Clearing Memory
If you need to reset conversation context:
```python
session.clear_memory()  # Clears in-memory history
```

## Benefits

### For Students 👧👦
- **Natural conversations**: No need to repeat context
- **Follow-up questions**: "Tell me more" or "What about the other one" works perfectly
- **Learning continuity**: LLM remembers what was already explained
- **Better engagement**: More human-like interaction

### For Teachers/Parents 👨‍🏫👩‍🏫
- **Review conversations**: Full chat history saved in database
- **Track learning**: See what topics were discussed
- **Session continuity**: Students can continue where they left off

### For Developers 💻
- **Simple implementation**: Automatic history management
- **Optimized performance**: Smart message limiting
- **Works with both OpenAI and Anthropic**: Unified interface
- **Database-backed**: All conversations persisted

## Technical Details

### Modified Files
1. **mimi_llm_session.py**
   - Added MongoDB connection for history retrieval
   - New methods: `_load_conversation_history()`, `_add_to_history()`, `_build_messages_with_history()`
   - Updated `_call_openai()` and `_call_anthropic()` to include history
   - Enhanced `process_text()` to save messages to history

### Memory Flow
```
1. Session starts → Load last 20 messages from DB
2. User asks question → Add to in-memory history
3. Build LLM prompt → Include system + history + current message
4. LLM responds → Add response to in-memory history
5. Save to DB → /mimi-save-chat endpoint handles persistence
6. Repeat steps 2-5
```

### LLM Message Format

**OpenAI:**
```python
[
  {"role": "system", "content": "You are Mimi..."},
  {"role": "user", "content": "Previous question"},
  {"role": "assistant", "content": "Previous answer"},
  {"role": "user", "content": "Current question"}
]
```

**Anthropic:**
```python
# System prompt separate
system = "You are Mimi..."
messages = [
  {"role": "user", "content": "Previous question"},
  {"role": "assistant", "content": "Previous answer"},
  {"role": "user", "content": "Current question"}
]
```

## Testing the Feature

### Basic Test
1. Start a session: `POST /start-mimi-session`
2. Ask: "What is photosynthesis?"
3. Ask: "Why is it important?" (should reference photosynthesis without re-explaining)
4. Ask: "Tell me more" (should continue from previous context)

### Advanced Test
1. Ask a series of related questions
2. Check database: `db.mimi_chats.findOne({session_id: "..."})`
3. Verify messages array contains full history
4. Restart session with same session_id
5. Verify LLM remembers previous conversation

### Memory Stats Endpoint (Optional)
You can add this to `app.py` to debug memory:
```python
@app.route('/mimi-memory-stats', methods=['GET'])
def mimi_memory_stats():
    session_id = request.args.get('session_id', '')
    session = _mimi_sessions.get(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(session.get_memory_stats())
```

## Troubleshooting

### "LLM not remembering previous messages"
- Check if `session_id` is consistent across requests
- Verify messages are being saved to database
- Ensure `_load_conversation_history()` is being called

### "Token limit exceeded" error
- Reduce `max_history_messages` in config
- Keep responses shorter (already set to 2-3 sentences)
- Monitor conversation length

### "Performance is slow"
- Conversation history loads once per session (first call only)
- Database queries are optimized (single find by session_id)
- Consider adding index: `db.mimi_chats.createIndex({session_id: 1})`

## Future Enhancements

### Possible Improvements
1. **Semantic search**: Find relevant past conversations across sessions
2. **Topic extraction**: Automatically tag conversations by subject
3. **Learning profiles**: Build long-term student knowledge models
4. **Memory compression**: Summarize old conversations to extend context
5. **Multi-session memory**: Remember student across different days

### Token Optimization
- Use GPT-4o-mini's larger context window (128k tokens)
- Implement rolling summarization for very long conversations
- Store embeddings for semantic retrieval

## Summary

✅ **What Changed:**
- LLM now remembers entire conversation history
- Automatic loading from database
- Context-aware responses
- Works with both OpenAI and Anthropic

✅ **What Stayed the Same:**
- Message saving flow (/mimi-save-chat)
- Session management
- API endpoints
- Database schema

🎯 **Result:** Mimi is now a true conversational tutor that remembers everything and provides contextually relevant answers!
