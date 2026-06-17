import os
import re
import json
import requests
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
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

try:
    import anthropic as _anthropic_sdk
except ImportError:
    _anthropic_sdk = None

# Module-level singletons — one HTTP connection pool reused for every question
# (avoids 100-300ms of TCP+TLS setup per request)
_openai_singleton  = None
_anthropic_singleton = None

def _get_openai_singleton(api_key: str):
    global _openai_singleton
    if _openai_singleton is None and _openai_sdk and api_key:
        _openai_singleton = _openai_sdk.OpenAI(api_key=api_key, timeout=8.0)
    return _openai_singleton

def _get_anthropic_singleton(api_key: str):
    global _anthropic_singleton
    if _anthropic_singleton is None and _anthropic_sdk and api_key:
        _anthropic_singleton = _anthropic_sdk.Anthropic(api_key=api_key, timeout=8.0)
    return _anthropic_singleton


# Regex to extract the "text" field from partial streaming JSON.
# Matches as soon as the value's closing quote is followed by "," or "}"
_TEXT_FIELD_RE = re.compile(r'"text"\s*:\s*"((?:[^"\\]|\\.)*?)"(?=\s*[,}])')

def _try_extract_text(s: str):
    """Extract the 'text' JSON field from a partial (streaming) JSON string."""
    m = _TEXT_FIELD_RE.search(s)
    if not m:
        return None
    raw = m.group(1)
    return raw.replace('\\"', '"').replace('\\n', ' ').replace('\\\\', '\\')


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

    TOPIC_REQUEST_PHRASES = [
        "what topics", "which topics", "what have we discussed",
        "what did we talk", "what topics did we", "what did we learn",
        "list topics", "show topics", "our topics", "topics we covered",
        "what we talked about", "remind me what we", "what all we discussed",
        "tell me what we", "what all did we", "what have we learned",
        "what subjects", "recap our topics",
    ]

    WEATHER_PHRASES = ["weather", "temperature", "forecast", "raining", "humid", "snowing"]
    # Weak signal words — ambiguous on their own ("hot dog"), only count as
    # weather intent when paired with a weather-ish question pattern below.
    WEATHER_WEAK_WORDS = ["hot", "cold", "sunny", "rainy", "windy", "cloudy", "snow"]
    DATETIME_PHRASES = ["what day", "what's the date", "what is the date", "today's date",
                         "current time", "what year is it"]
    NEWS_PHRASES = ["news", "what's happening", "what is happening",
                    "current events", "what happened today", "in the news"]
    CITY_STOPWORDS = {"today", "todays", "today's", "now", "right", "current", "outside", "here",
                       "currently", "please", "like", "is", "it", "the", "a", "an", "my", "your",
                       "our", "this", "that"}

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
        self.tavily_key    = os.environ.get("TAVILY_API_KEY")
        self.timezone      = os.environ.get("MIMI_TIMEZONE", "Asia/Kolkata")

        # Real-time data block for the CURRENT turn only — computed fresh in
        # process_text() and read by _build_system_prompt(). Never persisted.
        self._realtime_block = ""

        # ── Three-tier memory ──────────────────────────────────────────────────
        # SHORT-TERM  : conversation_history — all turns of THIS session (in-memory)
        # CONTEXT     : last N turns sent to LLM as messages array (sliding window)
        # LONG-TERM   : long_term_summary — compact text built from previous sessions
        self.conversation_history = []   # short-term: current session Q&A
        self.long_term_summary    = ""   # long-term: compact previous-sessions text
        self.topics_discussed     = []   # topic tracking across sessions
        self.history_loaded       = False  # flag — avoids double DB load
        self.max_context_turns    = 4    # send last 4 turns (8 msgs) — fewer tokens = faster

        self.memory_router = None
        self.memory_mode   = "basic"

        logger.info(
            "MimiLLMSession: student=%s session=%s openai=%s anthropic=%s",
            student_name, session_id, bool(self.openai_key), bool(self.anthropic_key)
        )

    # ── Memory Methods ──────────────────────────────────────────────────────

    def _build_long_term_summary(self):
        """
        LONG-TERM MEMORY: scan last 5 previous sessions and produce a compact
        text summary instead of raw Q&A pairs.  Token-efficient and clearly
        labelled so the LLM knows this is *prior* context.
        """
        if not self.student_name:
            return ""
        try:
            prev_docs = list(_mimi_chats.find(
                {
                    "student_name": {"$regex": f"^{self.student_name}$", "$options": "i"},
                    "session_id":   {"$ne": self.session_id},
                },
                sort=[("updated_at", -1)],
                limit=5,
            ))
            if not prev_docs:
                return ""

            # Collect topics (unique, ordered by most recent first)
            seen_topics: set = set()
            all_topics: list = []
            last_date = prev_docs[0].get("date", "")
            for doc in prev_docs:
                for msg in doc.get("messages", []):
                    t = (msg.get("topic") or "").strip()
                    if t and t.lower() not in seen_topics:
                        seen_topics.add(t.lower())
                        all_topics.append(t)

            parts = []
            if last_date:
                parts.append(f"Last session: {last_date}")
            if all_topics:
                parts.append(f"Topics already discussed: {', '.join(all_topics[:15])}")
            summary = " | ".join(parts)
            logger.info("[LTM] Summary built: %s", summary[:120])
            return summary
        except Exception as e:
            logger.error("[LTM] Failed: %s", e)
            return ""

    def load_history(self):
        """
        Load all three memory tiers from MongoDB.
        Called eagerly at session start so the first question has zero DB latency.
        """
        if self.history_loaded:
            return
        self.history_loaded = True

        # ── SHORT-TERM: restore current-session turns from DB ──────────
        # (needed if the worker restarted between turns)
        try:
            if self.session_id:
                doc = _mimi_chats.find_one({"session_id": self.session_id})
                if doc:
                    for msg in doc.get("messages", []):
                        q = msg.get("question", "")
                        a = msg.get("answer",   "")
                        if q: self.conversation_history.append({"role": "user",      "content": q})
                        if a: self.conversation_history.append({"role": "assistant", "content": a})
            logger.info("[STM] %d current-session messages loaded", len(self.conversation_history))
        except Exception as e:
            logger.error("[STM] Load failed: %s", e)

        # ── LONG-TERM: compact previous-sessions summary ────────────────
        self.long_term_summary = self._build_long_term_summary()

        # ── TOPICS: all topics from previous + current sessions ─────────
        self._load_topics_from_history()

    # Keep old name as alias so any existing callers don't break
    def _load_conversation_history(self):
        self.load_history()

    def _add_to_history(self, role, content):
        """Add a turn to SHORT-TERM memory (in-memory, current session only)."""
        if not content:
            return
        self.conversation_history.append({"role": role, "content": content})

    def clear_memory(self):
        self.conversation_history = []
        self.history_loaded = False
        logger.info("[Memory] Cleared for session %s", self.session_id)

    # ── Topic Memory Methods ─────────────────────────────────────────────────

    def _is_topic_request(self, text):
        t = text.lower().strip()
        return any(phrase in t for phrase in self.TOPIC_REQUEST_PHRASES)

    def _load_topics_from_history(self):
        """Load topics from previous sessions and current session messages."""
        try:
            topics = []
            if self.student_name:
                prev_sessions = list(_mimi_chats.find(
                    {
                        "student_name": {"$regex": f"^{self.student_name}$", "$options": "i"},
                        "session_id":   {"$ne": self.session_id}
                    },
                    sort=[("updated_at", -1)],
                    limit=3
                ))
                for prev_doc in prev_sessions:
                    for msg in prev_doc.get("messages", []):
                        t = (msg.get("topic") or "").strip()
                        if t:
                            topics.append(t)

            if self.session_id:
                session_doc = _mimi_chats.find_one({"session_id": self.session_id})
                if session_doc:
                    for msg in session_doc.get("messages", []):
                        t = (msg.get("topic") or "").strip()
                        if t:
                            topics.append(t)

            seen = set()
            unique = []
            for t in topics:
                key = t.lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(t)

            self.topics_discussed = unique
            logger.info(f"[Topics] Loaded {len(unique)} topics for {self.student_name}")
        except Exception as e:
            logger.error(f"[Topics] Failed to load topics: {e}")

    def _build_topic_list_response(self):
        name = self.student_name or "friend"
        seen = set()
        unique = []
        for t in self.topics_discussed:
            key = t.lower()
            if key not in seen:
                seen.add(key)
                unique.append(t)

        if not unique:
            text = (
                f"Hmm, we haven't explored any topics yet {name}! "
                "Ask me anything — space, animals, science, history — what sounds fun?"
            )
            return {"text": text, "topics_list": [], "image_url": None, "yt_video": None, "topic": ""}

        if len(unique) == 1:
            text = f"So far we talked about {unique[0]}! Want to go deeper into that, or explore something totally new?"
        else:
            topics_str = ", ".join(unique[:-1]) + f" and {unique[-1]}"
            text = (
                f"Oh {name}, we've covered so many cool things — {topics_str}! "
                "Which one do you want to dive deeper into?"
            )
        return {"text": text, "topics_list": unique, "image_url": None, "yt_video": None, "topic": ""}

    def get_memory_stats(self):
        """Get statistics about current conversation memory."""
        return {
            "messages_in_memory": len(self.conversation_history),
            "max_messages": self.max_history_messages,
            "session_id": self.session_id,
            "student_name": self.student_name
        }

    def _build_messages_with_history(self, system_prompt, user_message):
        """
        Build the messages array for the LLM call using all three memory tiers.

        Layout:
          [system]            ← system prompt (includes long-term summary)
          [user/assistant]*   ← CONTEXT MEMORY: last max_context_turns turns of this session
          [user]              ← current question
        """
        messages = [{"role": "system", "content": system_prompt}]

        # CONTEXT MEMORY: send last N turns of the current session
        context_msgs = self.conversation_history[-(self.max_context_turns * 2):]
        for msg in context_msgs:
            if msg["role"] != "system":
                messages.append(msg)

        messages.append({"role": "user", "content": user_message})
        return messages

    # ── Real-time data ───────────────────────────────────────────────────────

    _CITY_PATTERNS = [
        r"\b(?:weather|temperature|forecast|raining|sunny|cold|hot)\b.*?\b(?:in|at|for|of)\b\s+"
        r"([A-Za-z][A-Za-z\s]{1,30}?)(?:\?|$|[.,!]|\s+(?:right\s+now|today|now|currently)\b)",
        r"\b(?:in|at|for|of)\b\s+([A-Za-z][A-Za-z\s]{1,30}?)\s+\b(?:weather|temperature|forecast)\b",
        r"\btoday'?s?\s+([A-Za-z][A-Za-z\s]{1,30}?)\s+\b(?:weather|temperature|forecast)\b",
        r"\b([A-Za-z]+)\s+\b(?:weather|temperature|forecast)\b",
    ]

    def _detect_realtime_intents(self, text: str) -> set:
        t = text.lower()
        intents = set()
        weak_weather_hit = any(re.search(rf"\b{w}\b", t) for w in self.WEATHER_WEAK_WORDS) and \
            re.search(r"\b(is it|outside|out there|today|right now)\b", t)
        if any(p in t for p in self.WEATHER_PHRASES) or weak_weather_hit:
            intents.add("weather")
        if any(p in t for p in self.DATETIME_PHRASES) or \
           re.search(r"\b(what'?s?|tell me|current|today'?s?)\b.*\b(date|day|time|year)\b", t):
            intents.add("datetime")
        if any(p in t for p in self.NEWS_PHRASES):
            intents.add("news")
        return intents

    def _extract_city(self, text: str):
        t = text.strip()
        for pattern in self._CITY_PATTERNS:
            m = re.search(pattern, t, re.IGNORECASE)
            if not m:
                continue
            words = [w for w in m.group(1).strip().split() if w.lower() not in self.CITY_STOPWORDS]
            city = " ".join(words).strip()
            if city and len(city) > 1:
                return city
        return None

    def _get_current_datetime_str(self) -> str:
        now = datetime.now(ZoneInfo(self.timezone))
        return now.strftime("%A, %B %d, %Y, %I:%M %p (%Z)")

    def _fetch_weather(self, city: str):
        try:
            r = requests.get(f"https://wttr.in/{city}", params={"format": "j1"}, timeout=3)
            cur = r.json().get("current_condition", [{}])[0]
            temp = cur.get("temp_C")
            desc = (cur.get("weatherDesc", [{}])[0] or {}).get("value")
            if temp and desc:
                return f"{temp}°C, {desc}"
        except Exception as e:
            logger.error("Weather fetch failed for %s: %s", city, e)
        return None

    def _fetch_kid_news(self, query: str):
        if not self.tavily_key:
            return None
        try:
            r = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.tavily_key,
                    "query": f"{query} kid friendly news today",
                    "search_depth": "basic",
                    "max_results": 3,
                    "include_answer": True,
                },
                timeout=4,
            )
            data = r.json()
            answer = data.get("answer")
            if answer:
                return answer[:400]
            titles = [res.get("title", "") for res in data.get("results", [])[:3] if res.get("title")]
            if titles:
                return "; ".join(titles)
        except Exception as e:
            logger.error("Tavily news fetch failed: %s", e)
        return None

    def _build_realtime_block(self, user_text: str) -> str:
        """
        Fetch live data for THIS turn only, based on detected intent in user_text.
        Returns a short text block to inject into the system prompt, or "" if
        no real-time intent was detected.
        """
        intents = self._detect_realtime_intents(user_text)
        if not intents:
            return ""

        lines = []
        if "datetime" in intents:
            lines.append(f"Current date & time: {self._get_current_datetime_str()}")

        if "weather" in intents:
            city = self._extract_city(user_text)
            if city:
                live = self._fetch_weather(city)
                lines.append(f"Live weather in {city}: {live}" if live else
                             f"(Weather lookup for {city} failed — apologize briefly and suggest trying again.)")
            else:
                lines.append("(Child asked about weather but gave no city — ask them which city/place they're in.)")

        if "news" in intents:
            news = self._fetch_kid_news(user_text)
            lines.append(f"Latest kid-safe news snippet: {news}" if news else
                         "(No live news available right now — answer from general knowledge and say news may be a bit old.)")

        return "\n".join(lines)

    # ── Prompt builder ────────────────────────────────────────────────────────

    def get_memory_context(self) -> str:
        """
        Compact text summary of all memory tiers, for injection into the system prompt:
          - long-term summary (past sessions, from MongoDB)
          - topics already discussed (across past + current session)
          - working memory (last few turns of THIS session)
        """
        # NOTE: working memory (recent turns of THIS session) is intentionally
        # excluded here — _build_messages_with_history() already sends those
        # turns as separate user/assistant messages, so repeating them here
        # would double the tokens for no benefit.
        parts = []
        if self.long_term_summary:
            parts.append(f"Past sessions: {self.long_term_summary}")
        if self.topics_discussed:
            parts.append(f"Topics already discussed: {', '.join(self.topics_discussed[:15])}")

        return "\n".join(parts) if parts else "No prior memory yet — this is a fresh start."

    def _build_system_prompt(self) -> str:
        name = self.student_name or "friend"

        memory_prompt = (
            "Always check the memory context below before answering. "
            "If the child asks about something previously discussed, reference it naturally "
            "(e.g. \"Last time we talked about planets - remember Jupiter?\"). "
            "Connect new questions to existing knowledge when it fits naturally. "
            "If a fact is new, you may briefly say you'll remember it."
        )

        playful_prompt = (
            f"You are Mimi - {name}'s playful, magical AI learning buddy, like a fun older sister. "
            "Warm, excited, full of curiosity. Use expressive words (\"Wow!\", \"Hooray!\", \"Let's explore!\"), "
            "simple child-friendly humour, and occasional emojis (max 1-2). "
            "Turn learning into a tiny story or game. Celebrate correct answers. "
            "If the child says \"I don't know\", encourage them warmly. "
            "Use everyday examples for tricky ideas. English only."
        )

        memory_context = self.get_memory_context()
        realtime_block = (
            f"\n\nREAL-TIME DATA (fetched just now — treat as accurate and current, "
            f"weave it naturally into your answer):\n{self._realtime_block}"
            if self._realtime_block else ""
        )

        media_rule = (
            "MEDIA: only fill image_search_term/youtube_search_term when the answer's main subject is a specific, "
            'concrete, picturable thing — an animal, place, object, person, planet, plant, vehicle, etc. '
            '(e.g. "national animal of India" -> bengal tiger -> fill both; "biggest ocean creature" -> blue whale -> fill both). '
            "Leave BOTH as empty strings \"\" for greetings, small talk, opinions, feelings, yes/no answers, "
            "math, abstract ideas, follow-up clarifying questions, or anything with no single concrete visual subject."
        )

        prompt = (
            f"{memory_prompt}\n\n{playful_prompt}\n\n"
            f"Current memory context:\n{memory_context}"
            f"{realtime_block}\n\n"
            f'RULES: Vary openers ("Oh wow!", "No way!", "I love that!", "Wait—"). '
            f"Give 1 cool fact. End with 1 easy open-ended question. Max 30 words. Never repeat facts from this chat.\n"
            f"{media_rule}\n"
            f'REPLY AS JSON ONLY: {{"text":"...","image_search_term":"...","youtube_search_term":"... for kids","topic":"..."}}'
        )
        return prompt, 120

    # ── LLM helpers ───────────────────────────────────────────────────────────

    def _call_openai(self, prompt):
        api_key = self.openai_key
        if not api_key:
            return None

        system_instructions, max_tokens = self._build_system_prompt()
        messages = self._build_messages_with_history(system_instructions, prompt)

        try:
            client = _get_openai_singleton(api_key)
            if client is None:
                return None
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.8,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content or None
        except Exception as e:
            logger.error("OpenAI call failed: %s", e)
            return None

    def _call_anthropic(self, prompt):
        api_key = self.anthropic_key
        if not api_key:
            return None

        system_instructions, max_tokens = self._build_system_prompt()
        messages = [m for m in self.conversation_history if m["role"] != "system"]
        messages.append({"role": "user", "content": prompt})

        try:
            client = _get_anthropic_singleton(api_key)
            if client is None:
                return None
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                system=system_instructions,
                max_tokens=max_tokens,
                messages=messages,
            )
            return resp.content[0].text
        except Exception as e:
            logger.error("Anthropic call failed: %s", e)
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
                timeout=3,
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
                timeout=3,
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

    def _get_openai_streaming(self, user_text: str, tts_func):
        """
        Stream GPT-4o-mini. As soon as the 'text' JSON field is complete in the
        stream, kick off TTS in a background thread so TTS overlaps with the
        remaining LLM generation time (~0.5-1s saving).
        Returns result dict or None on any error (caller falls back to non-streaming).
        """
        import concurrent.futures
        client = _get_openai_singleton(self.openai_key)
        if not client:
            return None

        system_prompt, max_tokens = self._build_system_prompt()
        messages = self._build_messages_with_history(system_prompt, user_text)

        full_text = ""
        tts_future = None
        tts_text = None
        tts_ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        try:
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.8,
                max_tokens=max_tokens,
                stream=True,
            )
            for chunk in stream:
                delta = chunk.choices[0].delta.content
                if not delta:
                    continue
                full_text += delta
                # Fire TTS as soon as "text" field is fully received.
                # We know it's complete when "image_search_term" key appears next.
                if tts_future is None and '"image_search_term"' in full_text:
                    extracted = _try_extract_text(full_text)
                    if extracted:
                        tts_text = extracted
                        tts_future = tts_ex.submit(tts_func, extracted)
        except Exception as e:
            logger.error("OpenAI streaming error: %s", e)
            tts_ex.shutdown(wait=False)
            return None

        data = self._parse_json_response(full_text)
        resp_text = (data.get("text") if data else None) or tts_text or full_text.strip()
        topic     = (data.get("topic") if data else "") or ""
        search    = (data.get("image_search_term") if data else "") or ""
        yt_search = (data.get("youtube_search_term") if data else "") or search

        # Media fetches run while we wait on TTS (which started early)
        media_ex = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        img_fut = yt_fut = None
        if search:    img_fut = media_ex.submit(self._fetch_wikimedia_image, search)
        if yt_search: yt_fut  = media_ex.submit(self._fetch_youtube_video_url, yt_search)

        audio = None
        if tts_future:
            try:   audio = tts_future.result(timeout=8)
            except Exception: pass
        elif resp_text:
            # Text field wasn't extracted early (very short response) — run TTS now
            try:   audio = tts_func(resp_text)
            except Exception: pass
        tts_ex.shutdown(wait=False)

        image_url = yt_video = None
        if img_fut:
            try:   image_url = img_fut.result(timeout=2)
            except Exception: pass
        if yt_fut:
            try:   yt_video  = yt_fut.result(timeout=2)
            except Exception: pass
        media_ex.shutdown(wait=False)

        logger.info("[stream] done — tts:%s img:%s yt:%s", bool(audio), bool(image_url), bool(yt_video))
        return {"text": resp_text, "image_url": image_url, "yt_video": yt_video, "audio": audio, "topic": topic}

    def _get_llm_response_json(self, user_text, tts_func=None):
        """
        Get LLM response and run TTS + media fetch in parallel.
        Tries OpenAI streaming first (overlaps TTS with LLM generation).
        Falls back to non-streaming / Anthropic on error.
        """
        import concurrent.futures

        # ── Fast path: OpenAI streaming ──────────────────────────────────────
        if self.openai_key and tts_func:
            result = self._get_openai_streaming(user_text, tts_func)
            if result:
                return result

        # ── Fallback: non-streaming ──────────────────────────────────────────
        llm_text = None
        openai_err = anthropic_err = None

        if self.openai_key:
            try:
                llm_text = self._call_openai(user_text)
            except Exception as e:
                openai_err = str(e)

        if not llm_text and self.anthropic_key:
            try:
                llm_text = self._call_anthropic(user_text)
            except Exception as e:
                anthropic_err = str(e)

        if not llm_text:
            msg = ("No API keys configured." if not self.openai_key and not self.anthropic_key
                   else f"AI Error. OpenAI: {openai_err or 'failed'}, Anthropic: {anthropic_err or 'failed'}")
            return {"text": msg, "image_url": None, "yt_video": None, "audio": None, "topic": ""}

        data = self._parse_json_response(llm_text)
        resp_text = (data.get("text") if data else llm_text.strip()) or ""
        topic     = (data.get("topic") if data else "") or ""

        if not data:
            return {"text": resp_text, "image_url": None, "yt_video": None, "audio": None, "topic": ""}

        search    = data.get("image_search_term") or ""
        yt_search = data.get("youtube_search_term") or search

        # ── All three I/O tasks in parallel: TTS + image + youtube ──────────
        # IMPORTANT: don't use `with` — that blocks until ALL threads finish.
        # Instead, collect results with short timeouts then shutdown without waiting.
        # Slow Wikimedia/YouTube threads run in background and die when they timeout.
        logger.info("[mimi] Parallel: TTS + image + youtube")
        ex = concurrent.futures.ThreadPoolExecutor(max_workers=3)
        futures = {}
        if tts_func and resp_text:
            futures["tts"]   = ex.submit(tts_func, resp_text)
        if search:
            futures["image"] = ex.submit(self._fetch_wikimedia_image, search)
        if yt_search:
            futures["yt"]    = ex.submit(self._fetch_youtube_video_url, yt_search)

        audio = image_url = yt_video = None
        if "tts" in futures:
            try:   audio     = futures["tts"].result(timeout=8)
            except Exception: pass
        if "image" in futures:
            try:   image_url = futures["image"].result(timeout=2)
            except Exception: pass
        if "yt" in futures:
            try:   yt_video  = futures["yt"].result(timeout=2)
            except Exception: pass

        ex.shutdown(wait=False)   # don't block — slow threads finish in background
        logger.info("[mimi] Done — tts:%s image:%s yt:%s", bool(audio), bool(image_url), bool(yt_video))

        return {
            "text":      resp_text,
            "image_url": image_url,
            "yt_video":  yt_video,
            "audio":     audio,
            "topic":     topic,
        }

    # ── Public API ─────────────────────────────────────────────────────────────

    def preload_history(self):
        """
        Eagerly warm all three memory tiers.
        Called from /start-mimi-session in a background thread so the first
        question response has zero extra DB latency.
        """
        self.load_history()

    def process_text(self, user_text, tts_func=None):
        """
        Called by /mimi-text-chat for each user utterance.
        tts_func: optional callable — runs in parallel with media fetch for lower latency.
        Returns the LLM response dict (includes "audio" key if tts_func provided).
        """
        self.current_action = "thinking"
        self.current_text   = "Thinking..."

        # Load all three memory tiers on first turn (history_loaded guards against double-load).
        # preload() is called at session start so this is usually already done.
        if not self.history_loaded:
            self.load_history()

        try:
            # ── Topic list shortcut — skip LLM entirely ──────────────
            if self._is_topic_request(user_text):
                result = self._build_topic_list_response()
                self._add_to_history("user", user_text)
                self._add_to_history("assistant", result.get("text", ""))
                self.current_text   = result.get("text", "")
                self.current_action = "done"
                result["audio"]     = None   # caller will do TTS separately if needed
                logger.info(f"[Topics] Topic list returned — {len(result.get('topics_list', []))} topics")
                return result

            # ── Real-time data (weather/date-time/news) for THIS turn only ──
            self._realtime_block = self._build_realtime_block(user_text)
            if self._realtime_block:
                logger.info("[Realtime] Injected: %s", self._realtime_block[:120])

            # ── Normal LLM flow — TTS runs in parallel with media fetch ──
            result = self._get_llm_response_json(user_text, tts_func=tts_func)

            # Extract and track topic
            topic = (result.get("topic") or "").strip()
            if topic:
                key = topic.lower()
                if key not in {t.lower() for t in self.topics_discussed}:
                    self.topics_discussed.append(topic)
            result["topic"] = topic

            # Update in-memory history AFTER the LLM call
            self._add_to_history("user", user_text)
            assistant_response = result.get("text", "")
            if assistant_response:
                self._add_to_history("assistant", assistant_response)

            self.current_text   = assistant_response
            self.current_image  = result.get("image_url")
            self.current_video  = result.get("yt_video")
            self.current_action = "done"

            logger.info(
                "[Memory] %d msgs | [Topics] %d topics",
                len(self.conversation_history), len(self.topics_discussed)
            )
            return result
        except Exception as e:
            logger.error("Error in process_text: %s", e)
            error_msg = "Sorry, I had a little hiccup! Ask me again?"
            self._add_to_history("assistant", error_msg)
            return {"text": error_msg, "error": str(e), "topic": "", "audio": None}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    s = MimiLLMSession(student_age=12)
    print(s.process_text("What is the capital of France?"))
