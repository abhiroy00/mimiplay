import os
import json
import requests
import logging
from datetime import datetime, timezone
from pymongo import MongoClient

logger = logging.getLogger(__name__)

# MongoDB connection for conversation memory
MONGO_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
_mongo_client = MongoClient(MONGO_URI)
_db = _mongo_client["AlexiDB"]
_mimi_chats = _db["mimi_chats"]

# Advanced memory system (optional - falls back gracefully)
try:
    from memory_system import MemoryRouter
    ADVANCED_MEMORY_AVAILABLE = True
    logger.info("[MimiLLM] Advanced multi-tier memory system available")
except ImportError:
    ADVANCED_MEMORY_AVAILABLE = False
    logger.info("[MimiLLM] Using basic conversation memory (advanced system not installed)")

try:
    import openai as _openai_sdk
except ImportError:
    _openai_sdk = None


class MimiLLMSession:
    """
    LLM session for one student chat interaction.

    Lifecycle (per session_id):
      1. Instantiated by /start-mimi-session with student context
      2. process_text() called by /mimi-chat-audio for each user utterance
      3. Returns LLM response — DB save is handled by /mimi-save-chat in app.py
      4. session_ended flag set by /api/mimi/stop-session

    No server-side microphone, no background threads, no duplicate DB writes.
    """

    def __init__(self, openai_api_key=None, anthropic_api_key=None,
                 student_name="", session_id="", student_id=None, student_age=10):
        self.student_name = student_name
        self.session_id   = session_id
        self.student_id   = student_id
        self.student_age  = int(student_age) if student_age else 10  # Kept for compatibility but not used in prompts

        # Public state read by /mimi-get
        self.current_text       = None
        self.current_image      = None
        self.current_video      = None
        self.current_audio      = None
        self.current_audio_text = None
        self.current_action     = 'idle'
        self.session_ended      = False

        self.openai_key    = openai_api_key    or os.environ.get("OPENAI_API_KEY")
        self.anthropic_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.youtube_key   = os.environ.get("YOUTUBE_API_KEY")

        # Memory system selection
        self.use_advanced_memory = os.environ.get("USE_ADVANCED_MEMORY", "false").lower() == "true"
        
        if self.use_advanced_memory and ADVANCED_MEMORY_AVAILABLE and student_id:
            # Use advanced multi-tier memory system
            from memory_system import MemoryRouter
            self.memory_router = MemoryRouter(str(student_id), session_id)
            self.conversation_history = []  # Still maintain for compatibility
            self.memory_mode = "advanced"
            logger.info(
                "MimiLLMSession created for '%s' | session=%s with ADVANCED multi-tier memory",
                student_name, session_id
            )
        else:
            # Use basic conversation memory
            self.memory_router = None
            self.conversation_history = []  # In-memory cache of conversation
            self.memory_mode = "basic"
            logger.info(
                "MimiLLMSession created for '%s' | session=%s with basic conversation memory",
                student_name, session_id
            )
        
        # Conversation memory settings
        self.max_history_messages = 40  # Keep last 40 messages (20 turns) for long conversations

        logger.info(
            "MimiLLMSession: OpenAI=%s, Anthropic=%s, Memory=%s",
            bool(self.openai_key), bool(self.anthropic_key), self.memory_mode
        )

    # ── Conversation Memory Methods ──────────────────────────────────────────

    def _load_conversation_history(self):
        """Load recent conversation history from database."""
        try:
            if not self.session_id:
                return
            
            session_doc = _mimi_chats.find_one({"session_id": self.session_id})
            if not session_doc or "messages" not in session_doc:
                logger.info(f"[Memory] No previous conversation found for session {self.session_id}")
                return
            
            messages = session_doc.get("messages", [])
            # Keep only the most recent messages to avoid token limits
            recent_messages = messages[-self.max_history_messages:]
            
            # Convert to conversation history format
            self.conversation_history = []
            for msg in recent_messages:
                role = msg.get("role", "user")
                content = msg.get("message", "")
                if content:
                    self.conversation_history.append({
                        "role": role,
                        "content": content
                    })
            
            logger.info(f"[Memory] Loaded {len(self.conversation_history)} messages from history for session {self.session_id}")
        except Exception as e:
            logger.error(f"[Memory] Failed to load conversation history: {e}")
            self.conversation_history = []

    def _add_to_history(self, role, content):
        """Add a message to conversation history."""
        if not content:
            return
        
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        
        # Keep only recent messages to prevent memory bloat
        if len(self.conversation_history) > self.max_history_messages:
            self.conversation_history = self.conversation_history[-self.max_history_messages:]

    def clear_memory(self):
        """Clear conversation history. Useful for starting fresh or resolving context issues."""
        self.conversation_history = []
        logger.info(f"[Memory] Cleared conversation history for session {self.session_id}")

    def get_memory_stats(self):
        """Get statistics about current conversation memory."""
        return {
            "messages_in_memory": len(self.conversation_history),
            "max_messages": self.max_history_messages,
            "session_id": self.session_id,
            "student_name": self.student_name
        }

    def _build_messages_with_history(self, system_prompt, user_message):
        """Build messages array with conversation history for LLM."""
        messages = [{"role": "system", "content": system_prompt}]
        
        # If using advanced memory, build enhanced context
        if self.memory_mode == "advanced" and self.memory_router:
            try:
                context = self.memory_router.build_context(user_message)
                
                # Add context summary to system prompt
                if context.get("summary"):
                    enhanced_prompt = f"{system_prompt}\n\nCONTEXT FROM MEMORY:\n{context['summary']}"
                    messages[0]["content"] = enhanced_prompt
                
                # Add recent working memory (conversation)
                for msg in context.get("working", []):
                    if msg["role"] != "system":
                        messages.append({"role": msg["role"], "content": msg["content"]})
                
                # Add semantic facts as context
                if context.get("semantic"):
                    facts_text = "Relevant facts: " + "; ".join([f["fact"] for f in context["semantic"][:3]])
                    messages.append({"role": "system", "content": facts_text})
                
            except Exception as e:
                logger.error(f"[Memory] Advanced memory context build failed: {e}")
                # Fallback to basic history
                for msg in self.conversation_history:
                    if msg["role"] != "system":
                        messages.append(msg)
        else:
            # Basic memory: Add conversation history
            for msg in self.conversation_history:
                if msg["role"] != "system":
                    messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        return messages

    # ── Prompt builder ────────────────────────────────────────────────────────

    def _build_system_prompt(self) -> str:
        now = datetime.now()
        current_datetime = now.strftime("%A, %d %B %Y, %I:%M %p")
        name = self.student_name or "friend"
        max_tokens = 600

        prompt = f"""IDENTITY: You are Mimi — a warm, playful, and brilliant AI best friend for children aged 4–14. You are like an enthusiastic older sister who loves learning and genuinely wants {name} to love learning too. You ONLY speak English.

CORE MISSION: Keep {name} talking! Every response must make them want to reply. Your two goals are (1) teach something interesting and (2) pull out more words from {name} so they practise English naturally.

━━━ CONVERSATION STYLE ━━━
• Be enthusiastic and personal. Use "Wow!", "Oh that's so cool!", "I was JUST thinking about that!", "Great question!"
• ALWAYS end your text with one engaging follow-up question that invites {name} to respond. Make it specific and easy to answer.
• If {name} gives a short answer ("yes", "no", "ok", "idk"), gently dig deeper: "Yes! Tell me more — what made you think of that?" or "Hmm, what do YOU think happens next?"
• React to what {name} says BEFORE launching into facts: "Oh you love football? That's amazing!"
• Use their name ({name}) naturally in the conversation.

━━━ ENGLISH IMPROVEMENT (do this invisibly — never like a teacher) ━━━
• If {name} makes a grammar mistake, weave the correct form into your reply WITHOUT pointing it out. They said "I goed"? You say "Oh, you went there! That sounds so fun!"
• Introduce one interesting new word every few exchanges, explained in a child-friendly way: "Scientists call it 'bioluminescence' — it means the fish makes its own light, like a living torch!"
• Ask {name} to DESCRIBE things: "Can you describe what it looks like?", "How did it make you feel?"
• Praise good expression naturally: "I love how you described that!" or "That's exactly the right word!"

━━━ MEMORY & CONTINUITY (CRITICAL) ━━━
• Remember EVERYTHING from this session. Reference earlier topics, interests, and things {name} shared.
• Build connections: if they mentioned they like animals earlier and now ask about space, link them: "Since you love animals, you'd be amazed — there are tiny water bears that can survive in outer space!"
• After several exchanges, recap interests: "We've talked about so much — you really love space and animals, don't you?"
• Never repeat the same fact twice in one session.

━━━ KNOWLEDGE, FACTS & CURRENT EVENTS ━━━
• Today is {current_datetime}. Use this! Mention upcoming holidays, current season, recent world events by date context.
• Share ONE surprising fact per response: "Fun fact: Honey never expires — they found 3,000-year-old honey in Egyptian tombs that was still edible!"
• Relate everything to {name}'s world: compare to pizza, school, games, movies, things kids know.
• For news/world events: use the date to mention what is happening in the world right now (sports events, space missions, technology launches, festivals).
• Topics you love: science, space, animals, history, geography, technology, sports, world records, mysteries, food, inventions, languages, maths tricks, famous people, current events.

━━━ RESPONSE RULES ━━━
• Speak English only. 3–5 sentences in "text". MUST end with a question.
• Never be boring or lecture-like. Every sentence should feel like chatting with a friend.
• SAFETY: Never produce violent, sexual, or harmful content. Redirect gently to something interesting.

━━━ RESPONSE FORMAT ━━━
Reply ONLY with a JSON object — no text outside JSON.
Keys:
- "text": Your response (3–5 sentences, ends with a question to {name})
- "image_search_term": Specific Wikimedia Commons search term (e.g. "giant panda eating bamboo China")
- "youtube_search_term": YouTube search term — always include "for kids" unless topic already has it. NEVER null.

Example:
{{"text": "Elephants are absolutely incredible, {name}! Did you know they can recognise themselves in a mirror — only a handful of animals can do that, like dolphins and us humans! They also never forget their friends, even after many years apart. What's your favourite thing about elephants — is it their size, their trunk, or something else?", "image_search_term": "African elephant herd savanna wildlife", "youtube_search_term": "elephant facts for kids"}}"""

        return prompt, max_tokens

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _call_openai(self, prompt):
        api_key = self.openai_key
        if not api_key:
            return None
        
        # Load conversation history on first call
        if not self.conversation_history:
            self._load_conversation_history()
        
        system_instructions, max_tokens = self._build_system_prompt()
        user_message = prompt  # clean input; system prompt sets all context

        # Build messages with conversation history
        messages = self._build_messages_with_history(system_instructions, user_message)

        try:
            if _openai_sdk is not None:
                client = _openai_sdk.OpenAI(api_key=api_key)
                resp = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=messages,
                    temperature=0.8,
                    max_tokens=max_tokens,
                )
                text = resp.choices[0].message.content
                if text:
                    return text
                return None
        except Exception as e:
            logger.error("OpenAI SDK call failed: %s", e, exc_info=True)

        # HTTP fallback
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": max_tokens,
                },
                timeout=15, #timeout=60
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"] or None
        except Exception as e:
            logger.error("OpenAI HTTP call failed: %s", e, exc_info=True)
            return None

    def _call_anthropic(self, prompt):
        api_key = self.anthropic_key
        if not api_key:
            return None
        
        # Load conversation history on first call
        if not self.conversation_history:
            self._load_conversation_history()
        
        system_instructions, max_tokens = self._build_system_prompt()
        user_message = prompt  # clean input; system prompt sets all context

        # Build messages with conversation history (excluding system - Anthropic handles it separately)
        messages = []
        for msg in self.conversation_history:
            if msg["role"] != "system":
                messages.append(msg)
        messages.append({"role": "user", "content": user_message})
        
        try:
            import anthropic as _anth_sdk
            client = _anth_sdk.Anthropic(api_key=api_key)
            resp = client.messages.create(
                model="claude-3-haiku-20240307",
                system=system_instructions,  # Anthropic uses separate system parameter
                max_tokens=max_tokens,
                messages=messages,
            )
            return resp.content[0].text
        except ImportError:
            pass
        except Exception as e:
            logger.error("Anthropic SDK call failed: %s", e)

        # HTTP fallback
        try:
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "system": system_instructions,
                    "max_tokens": max_tokens,
                    "messages": messages,
                },
                timeout=12, #timeout=20,
            )
            r.raise_for_status()
            return r.json()["content"][0]["text"]
        except Exception as e:
            logger.error("Anthropic HTTP call failed: %s", e)
            return None

    def _parse_json_response(self, text):
        if not text:
            return None
        try:
            start = text.find("{")
            end   = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                return json.loads(text[start:end + 1])
        except Exception as e:
            logger.warning("Failed to parse JSON from LLM response: %s", e)
        return None

    def _fetch_wikimedia_image(self, search_term):
        try:
            r = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query", "generator": "search",
                    "gsrsearch": search_term, "gsrlimit": 5,
                    "gsrnamespace": 6, "prop": "imageinfo",
                    "iiprop": "url", "format": "json",
                },
                headers={"User-Agent": "MimiBot/1.0"},
                timeout=10,
            )
            for page in r.json().get("query", {}).get("pages", {}).values():
                url = page.get("imageinfo", [{}])[0].get("url")
                if url:
                    return url
        except Exception as e:
            logger.error("Wikimedia error: %s", e)
        return None

    def _fetch_youtube_video_url(self, search_term):
        api_key = self.youtube_key
        if not api_key:
            return None
        # Use standardized suffix for all children aged 4-14
        suffix = "for kids educational"
        q = search_term if any(s in search_term.lower() for s in ["for kids", "explained", "educational"]) \
            else f"{search_term} {suffix}"
        try:
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet", "q": q, "type": "video",
                    "safeSearch": "strict", "videoEmbeddable": "true",
                    "maxResults": 3, "key": api_key,
                },
                timeout=10,
            )
            for item in r.json().get("items", []):
                id_block = item.get("id", {})
                if id_block.get("kind") == "youtube#video":
                    video_id = id_block.get("videoId", "")
                    if video_id:
                        return f"https://www.youtube.com/embed/{video_id}"
        except Exception as e:
            logger.error("YouTube API error: %s", e)
        return None

    def _get_llm_response_json(self, user_text):
        # Check cache first for faster responses
        try:
            from cache_helper import get_cache
            cache = get_cache()
            
            if cache.enabled:
                # Generate context hash from recent conversation
                context_summary = str(self.conversation_history[-4:]) if len(self.conversation_history) > 0 else ""
                cached_response = cache.get(user_text, context_summary)
                
                if cached_response:
                    logger.info("[mimi] Returning cached response (instant!)")
                    return cached_response
        except Exception as e:
            logger.warning(f"[mimi] Cache check failed: {e}")
        
        # Not in cache, get fresh response
        text = None
        openai_err = anthropic_err = None

        if self.openai_key:
            try:
                text = self._call_openai(user_text)
            except Exception as e:
                openai_err = str(e)

        if not text and self.anthropic_key:
            try:
                text = self._call_anthropic(user_text)
            except Exception as e:
                anthropic_err = str(e)

        if not text:
            if not self.openai_key and not self.anthropic_key:
                msg = "No API keys configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY."
            else:
                msg = f"AI Error. OpenAI: {openai_err or 'failed'}, Anthropic: {anthropic_err or 'failed'}"
            return {"text": msg, "image_url": None, "yt_video": None}

        data = self._parse_json_response(text)
        if not data:
            response = {"text": text.strip(), "image_url": None, "yt_video": None}
            return response

        search    = data.get("image_search_term") or ""
        yt_search = data.get("youtube_search_term") or search or " ".join((data.get("text") or "").split()[:4])

        # Check if Celery is enabled for async media fetching
        use_celery = os.environ.get("USE_CELERY", "false").lower() == "true"
        
        if use_celery:
            # Async mode: Return text immediately, fetch media in background
            try:
                from tasks import fetch_wikimedia_image, fetch_youtube_video
                
                # Trigger async tasks (don't wait for results)
                if search:
                    fetch_wikimedia_image.delay(search)
                if yt_search:
                    fetch_youtube_video.delay(yt_search, self.youtube_key or "")
                
                logger.info("[mimi] Media fetching triggered async (Celery)")
                response = {
                    "text": data.get("text") or "",
                    "image_url": None,  # Will be fetched async
                    "yt_video": None,   # Will be fetched async
                }
            except ImportError:
                logger.warning("[mimi] Celery not available, falling back to parallel sync")
                use_celery = False
        
        if not use_celery:
            # Sync mode: Parallel fetch with reduced timeout
            import concurrent.futures
            image_url = None
            yt_video  = None
            
            logger.info("[mimi] Starting parallel sync fetch for image+youtube")
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = {}
                if search:
                    futures['image'] = executor.submit(self._fetch_wikimedia_image, search)
                if yt_search:
                    futures['yt'] = executor.submit(self._fetch_youtube_video_url, yt_search)
                
                # Reduced timeout for faster response (3s instead of 8s)
                if 'image' in futures:
                    try:
                        image_url = futures['image'].result(timeout=3)
                    except Exception:
                        image_url = None
                if 'yt' in futures:
                    try:
                        yt_video = futures['yt'].result(timeout=3)
                    except Exception:
                        yt_video = None
                
                logger.info("[mimi] Parallel fetch done — image:%s yt:%s", bool(image_url), bool(yt_video))
            
            response = {
                "text": data.get("text") or "",
                "image_url": image_url,
                "yt_video": yt_video,
            }
        
        # Cache the response for future requests
        try:
            from cache_helper import get_cache
            cache = get_cache()
            if cache.enabled:
                context_summary = str(self.conversation_history[-4:]) if len(self.conversation_history) > 0 else ""
                cache.set(user_text, response, context_summary)
        except Exception as e:
            logger.warning(f"[mimi] Cache save failed: {e}")
        
        return response

    # ── Public API ─────────────────────────────────────────────────────────────

    def process_text(self, user_text):
        """
        Called by /mimi-chat-audio for each user utterance.
        Returns the LLM response dict.
        DB save is intentionally NOT done here — /mimi-save-chat handles it.
        """
        self.current_action = "thinking"
        self.current_text   = "Thinking..."
        
        try:
            # Get LLM response FIRST — history does NOT yet contain this turn so
            # _build_messages_with_history won't duplicate the user message.
            result = self._get_llm_response_json(user_text)

            # Add both sides to history AFTER the call, in the correct order.
            self._add_to_history("user", user_text)
            assistant_response = result.get("text", "")
            if assistant_response:
                self._add_to_history("assistant", assistant_response)
            
            # Update advanced memory system if enabled
            if self.memory_mode == "advanced" and self.memory_router:
                try:
                    metadata = {
                        "image_url": result.get("image_url"),
                        "video_url": result.get("yt_video"),
                        "student_name": self.student_name
                    }
                    self.memory_router.update_memories(user_text, assistant_response, metadata)
                    logger.info(f"[Memory] Advanced memory updated for session {self.session_id}")
                except Exception as e:
                    logger.error(f"[Memory] Failed to update advanced memory: {e}")
            
            self.current_text   = assistant_response
            self.current_image  = result.get("image_url")
            self.current_video  = result.get("yt_video")
            self.current_action = "done"
            
            logger.info(f"[Memory] Conversation history now has {len(self.conversation_history)} messages (mode: {self.memory_mode})")
            return result
        except Exception as e:
            logger.error("Error in process_text: %s", e)
            error_msg = "Sorry, I encountered an error while thinking."
            self._add_to_history("assistant", error_msg)
            return {"text": error_msg, "error": str(e)}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s = MimiLLMSession(student_age=12)
    print(s.process_text("What is the capital of France?"))
