import os
import re
import json
import requests
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from extensions import db as _ext_db

logger = logging.getLogger(__name__)

_mimi_chats = _ext_db["mimi_chats"]
_qa_memory  = _ext_db["qa_memory"]   # one doc per Q&A turn, embedded for semantic recall

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


_EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dims, cheap — used for semantic recall only

def _embed_text(text: str, api_key: str):
    """Return an embedding vector for `text`, or None on any failure (caller degrades gracefully)."""
    if not text or not _openai_sdk or not api_key:
        return None
    try:
        client = _get_openai_singleton(api_key)
        if not client:
            return None
        resp = client.embeddings.create(model=_EMBEDDING_MODEL, input=text[:8000])
        return resp.data[0].embedding
    except Exception as e:
        logger.warning("[Embed] Failed to embed text: %s", e)
        return None


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

    FAREWELL_KEYWORDS = [
        "bye", "goodbye", "bye bye", "see you", "see ya", "good night",
        "goodnight", "i have to go", "i got to go", "i need to go",
        "i'm leaving", "i am leaving", "stop session", "end session",
        "ok bye", "tata", "alvida", "stop mimi", "close session",
    ]

    TOPIC_REQUEST_PHRASES = [
        "what topics", "which topics", "what have we discussed",
        "what did we talk", "what topics did we", "what did we learn",
        "list topics", "show topics", "our topics", "topics we covered",
        "what we talked about", "remind me what we", "what all we discussed",
        "tell me what we", "what all did we", "what have we learned",
        "what subjects", "recap our topics",
    ]

    RECALL_PHRASES = [
        # English
        "repeat that", "say that again", "say it again", "tell me again",
        "what did i ask", "what was my question", "previous question",
        "my last question", "what did i just ask", "what was the last question",
        "repeat your answer", "what did you say", "tell me what i asked",
        "can you repeat", "say again", "what did i ask about",
        "remind me what i asked", "what was my last question",
        # Hindi / Hinglish
        "phir bolo", "phir se bolo", "dobara bolo", "dobara batao",
        "phir batao", "kya pucha tha", "pehle kya pucha", "repeat karo",
    ]

    # Stop-words to strip when extracting a topic keyword from recall queries
    _RECALL_STOP = {
        "what", "did", "i", "ask", "about", "tell", "me", "again",
        "repeat", "that", "my", "last", "question", "say", "it", "the",
        "a", "an", "you", "please", "can", "could", "would", "know",
    }

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
        self.max_context_turns    = 8    # send last 8 turns (16 msgs) — enough to retain names/context from early in session

        self._advanced_context = ""
        self._profile_context  = ""
        if ADVANCED_MEMORY_AVAILABLE and student_id:
            try:
                self.memory_router = MemoryRouter(str(student_id), session_id)
                self.memory_mode   = "advanced"
                logger.info("[MimiLLM] Advanced memory router initialized for student=%s", student_id)
            except Exception as e:
                logger.warning("[MimiLLM] MemoryRouter init failed: %s", e)
                self.memory_router = None
                self.memory_mode   = "basic"
        else:
            self.memory_router = None
            self.memory_mode   = "basic"

        logger.info(
            "MimiLLMSession: student=%s session=%s openai=%s anthropic=%s mode=%s",
            student_name, session_id, bool(self.openai_key), bool(self.anthropic_key), self.memory_mode
        )

    # ── Memory Methods ──────────────────────────────────────────────────────

    def load_history(self):
        """
        Load all three memory tiers from MongoDB in a single scan.
        Called eagerly at session start so the first question has zero extra DB latency.
        """
        if self.history_loaded:
            return
        self.history_loaded = True

        # ── SHORT-TERM: restore current-session turns from DB ─────────────────
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
            logger.warning("[STM] Failed to load current session: %s", e)

        # ── LONG-TERM + TOPICS: single query over last 5 previous sessions ────
        if self.student_name:
            try:
                prev_docs = list(_mimi_chats.find(
                    {
                        "student_name": {"$regex": f"^{self.student_name}$", "$options": "i"},
                        "session_id":   {"$ne": self.session_id},
                    },
                    sort=[("updated_at", -1)],
                    limit=5,
                ))
                if prev_docs:
                    seen_topics: set = set()
                    all_topics:  list = []
                    last_date = prev_docs[0].get("date", "")
                    for doc in prev_docs:
                        for msg in doc.get("messages", []):
                            t = (msg.get("topic") or "").strip()
                            if t and t.lower() not in seen_topics:
                                seen_topics.add(t.lower())
                                all_topics.append(t)
                    self.topics_discussed  = all_topics[:15]
                    parts = []
                    if last_date:
                        parts.append(f"Last session: {last_date}")
                    if all_topics:
                        parts.append(f"Topics already discussed: {', '.join(all_topics[:15])}")
                    self.long_term_summary = " | ".join(parts)
                    logger.info("[LTM] Summary built: %s", self.long_term_summary[:120])
            except Exception as e:
                logger.error("[LTM] Failed: %s", e)

        # ── LONG-TERM SUMMARY: fold in the richer LLM-authored session summary ─
        # session_summaries is written by _generate_and_save_summary() on every
        # farewell, but was never read back until now — this is that read.
        if self.student_name:
            try:
                recent_summaries = list(_ext_db["session_summaries"].find(
                    {"student_name": {"$regex": f"^{self.student_name}$", "$options": "i"}},
                    sort=[("created_at", -1)],
                    limit=2,
                ))
                if recent_summaries:
                    summary_parts = []
                    key_facts: list = []
                    for doc in recent_summaries:
                        s = (doc.get("summary") or "").strip()
                        if s:
                            summary_parts.append(f"({doc.get('session_date', '')}) {s}")
                        for f in doc.get("key_facts", []):
                            if f and f not in key_facts:
                                key_facts.append(f)
                    extra = []
                    if summary_parts:
                        extra.append("Recent session summaries: " + " ".join(summary_parts))
                    if key_facts:
                        extra.append("Things already taught: " + "; ".join(key_facts[:8]))
                    if extra:
                        self.long_term_summary = (
                            (self.long_term_summary + " | " if self.long_term_summary else "")
                            + " | ".join(extra)
                        )
                        logger.info("[LTM] Folded in %d session summaries", len(recent_summaries))
            except Exception as e:
                logger.error("[LTM] session_summaries read failed: %s", e)

        # ── STUDENT PROFILE: load persisted facts from student_profiles ───────
        self._load_student_profile()

    def _load_student_profile(self):
        if not self.student_id:
            return
        try:
            profile = _ext_db["student_profiles"].find_one({"student_id": self.student_id})
            if not profile:
                self._profile_context = ""
                return
            p = [f"Student context: Name is {profile.get('name', self.student_name)}."]
            interests = profile.get("interests", [])
            if interests:
                p.append(f"Interested in: {', '.join(interests[:5])}.")
            struggling = profile.get("struggling_topics", [])
            if struggling:
                p.append(f"Needs help with: {', '.join(struggling[:3])}.")
            strengths = profile.get("progress", {}).get("strengths", [])
            if strengths:
                p.append(f"Strengths: {', '.join(strengths[:3])}.")
            self._profile_context = " ".join(p)
        except Exception as e:
            logger.warning("[Profile] Failed to load profile: %s", e)

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

    def _is_farewell(self, text: str) -> bool:
        lower = text.lower().strip()
        return any(kw in lower for kw in self.FAREWELL_KEYWORDS)

    def _is_topic_request(self, text):
        t = text.lower().strip()
        return any(phrase in t for phrase in self.TOPIC_REQUEST_PHRASES)


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

    # ── Recall / Repeat Methods ──────────────────────────────────────────────

    def _is_recall_request(self, text: str) -> bool:
        t = text.lower().strip()
        return any(phrase in t for phrase in self.RECALL_PHRASES)

    def _extract_recall_topic(self, text: str):
        """Return a keyword from queries like 'what did I ask about planets' → 'planets'."""
        words = [w.strip("?!.,") for w in text.lower().split()]
        keywords = [w for w in words if w and w not in self._RECALL_STOP and len(w) > 2]
        return keywords[0] if keywords else None

    def _get_last_qa(self):
        """Return (question, answer) of the most recent exchange in this session."""
        history = self.conversation_history
        # Walk backward to find last assistant message, then the user message before it
        for i in range(len(history) - 1, 0, -1):
            if history[i]["role"] == "assistant":
                # find the user turn just before it
                for j in range(i - 1, -1, -1):
                    if history[j]["role"] == "user":
                        return history[j]["content"], history[i]["content"]
        return None, None

    # Vector search score is Atlas's normalized similarity (~0-1 for cosine metric).
    # Below this, treat it as "no real match" rather than returning a bad guess.
    _VECTOR_RECALL_MIN_SCORE = 0.70

    def _search_qa_by_topic(self, keyword: str, full_query: str = None):
        """
        Search current session history first (exact keyword, instant), then past
        sessions via semantic vector search over qa_memory (falls back to the old
        regex search over mimi_chats if the search index isn't ready yet or the
        embedding call fails). Returns (question, answer) or (None, None).
        """
        full_query = full_query or keyword

        # 1. Current session (in-memory, instant, exact keyword match)
        for i, msg in enumerate(self.conversation_history):
            if msg["role"] == "user" and keyword in msg["content"].lower():
                # get the assistant reply that follows
                for j in range(i + 1, len(self.conversation_history)):
                    if self.conversation_history[j]["role"] == "assistant":
                        return msg["content"], self.conversation_history[j]["content"]

        # 2. Past sessions — semantic vector search (understands paraphrases, not just exact words)
        if self.student_id:
            try:
                vector = _embed_text(full_query, self.openai_key)
                if vector:
                    results = list(_qa_memory.aggregate([
                        {"$vectorSearch": {
                            "index":         "qa_memory_vector_index",
                            "path":          "embedding",
                            "queryVector":   vector,
                            "numCandidates": 50,
                            "limit":         1,
                            "filter":        {"student_id": self.student_id},
                        }},
                        {"$project": {"question": 1, "answer": 1, "_id": 0,
                                      "score": {"$meta": "vectorSearchScore"}}},
                    ]))
                    if results and results[0].get("score", 0) >= self._VECTOR_RECALL_MIN_SCORE:
                        logger.info("[VectorRecall] Match score=%.3f for query=%r",
                                    results[0]["score"], full_query[:60])
                        return results[0].get("question"), results[0].get("answer")
            except Exception as e:
                logger.warning("[VectorRecall] Search failed, falling back to keyword search: %s", e)

        # 3. Fallback — exact regex keyword search over mimi_chats (covers sessions from
        #    before qa_memory existed, and degrades gracefully if the vector index is missing)
        if self.student_name:
            try:
                past = list(_mimi_chats.find(
                    {
                        "student_name": {"$regex": f"^{self.student_name}$", "$options": "i"},
                        "session_id":   {"$ne": self.session_id},
                        "messages.question": {"$regex": keyword, "$options": "i"},
                    },
                    sort=[("updated_at", -1)],
                    limit=3,
                ))
                for doc in past:
                    for msg in doc.get("messages", []):
                        q = msg.get("question", "")
                        a = msg.get("answer", "")
                        if q and a and keyword in q.lower():
                            return q, a
            except Exception as e:
                logger.error("[Recall] MongoDB regex search failed: %s", e)

        return None, None

    def _embed_and_store_qa(self, question: str, answer: str, topic: str = ""):
        """
        Embed a Q&A turn and store it in qa_memory for later semantic recall.
        Runs in a background daemon thread — never blocks the response path.
        """
        try:
            vector = _embed_text(question, self.openai_key)
            if not vector:
                return
            _qa_memory.insert_one({
                "student_id":   self.student_id,
                "student_name": self.student_name,
                "session_id":   self.session_id,
                "question":     question,
                "answer":       answer,
                "topic":        topic or "",
                "embedding":    vector,
                "created_at":   datetime.now(timezone.utc).isoformat(),
            })
            logger.info("[QAEmbed] Stored embedded Q&A for %s", self.student_name)
        except Exception as e:
            logger.warning("[QAEmbed] Failed: %s", e)

    def _build_recall_response(self, question: str, answer: str) -> str:
        import random
        name = self.student_name or "friend"
        short_q = question[:80] + ("…" if len(question) > 80 else "")
        short_a = answer[:150] + ("…" if len(answer) > 150 else "")
        templates = [
            f"Ooh, you have a great memory, {name}! 🧠 You asked me: \"{short_q}\" — and I said: \"{short_a}\" Want to explore more?",
            f"Sure! 😊 You asked: \"{short_q}\" — here's what I told you: \"{short_a}\" Isn't that cool?",
            f"I remember! 🌟 You were curious about: \"{short_q}\" — and I said: \"{short_a}\" Shall we dive deeper?",
            f"Great question to revisit, {name}! ✨ You asked: \"{short_q}\" — my answer was: \"{short_a}\"",
        ]
        return random.choice(templates)

    def _generate_and_save_summary(self, history_snapshot: list):
        """
        Generate a rich session summary via LLM and store it in MongoDB.
        Called in a daemon background thread after farewell — never blocks a response.
        Requires at least 3 user turns to be worth summarising.
        """
        user_turns = [m for m in history_snapshot if m["role"] == "user"]
        if len(user_turns) < 3 or not self.student_name:
            return

        # Build compact conversation text (cap at 40 turns ≈ ~1500 tokens)
        lines = []
        for m in history_snapshot[:40]:
            speaker = self.student_name if m["role"] == "user" else "Mimi"
            lines.append(f"{speaker}: {m['content']}")
        conv_text = "\n".join(lines)

        summary_prompt = (
            f"Below is a learning session between a child named {self.student_name} and "
            f"an AI tutor called Mimi. Summarise it as JSON with these exact keys:\n"
            f"  topics    – list of 3-5 main subjects discussed (short phrases, e.g. 'solar system')\n"
            f"  questions – list of up to 5 interesting questions {self.student_name} asked (verbatim or paraphrased)\n"
            f"  key_facts – list of up to 5 short facts or things Mimi taught\n"
            f"  summary   – one sentence describing the overall session\n\n"
            f"Return ONLY valid JSON, no extra text.\n\n"
            f"CONVERSATION:\n{conv_text}"
        )

        data = None
        # Try OpenAI first, Anthropic as fallback
        if self.openai_key and _openai_sdk:
            try:
                client = _get_openai_singleton(self.openai_key)
                if client:
                    resp = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You summarise children's learning sessions as JSON."},
                            {"role": "user",   "content": summary_prompt},
                        ],
                        temperature=0.3,
                        max_tokens=280,
                    )
                    raw = resp.choices[0].message.content or ""
                    start, end = raw.find("{"), raw.rfind("}")
                    if start != -1 and end > start:
                        data = json.loads(raw[start:end + 1])
            except Exception as e:
                logger.warning("[Summary] OpenAI failed: %s", e)

        if not data and self.anthropic_key and _anthropic_sdk:
            try:
                client = _get_anthropic_singleton(self.anthropic_key)
                if client:
                    resp = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        system="You summarise children's learning sessions as JSON.",
                        messages=[{"role": "user", "content": summary_prompt}],
                        max_tokens=280,
                    )
                    raw = resp.content[0].text or ""
                    start, end = raw.find("{"), raw.rfind("}")
                    if start != -1 and end > start:
                        data = json.loads(raw[start:end + 1])
            except Exception as e:
                logger.warning("[Summary] Anthropic failed: %s", e)

        # Fallback: build summary from existing topics_discussed if LLM failed
        if not data:
            data = {
                "topics":    self.topics_discussed[:5],
                "questions": [m["content"][:100] for m in user_turns[:5]],
                "key_facts": [],
                "summary":   f"Session with {self.student_name} covering {', '.join(self.topics_discussed[:3]) or 'various topics'}.",
            }

        try:
            now = datetime.now(timezone.utc)
            _ext_db["session_summaries"].insert_one({
                "student_name":   self.student_name,
                "session_id":     self.session_id,
                "topics":         data.get("topics", []),
                "questions":      data.get("questions", []),
                "key_facts":      data.get("key_facts", []),
                "summary":        data.get("summary", ""),
                "msg_count":      len(user_turns),
                "session_date":   now.strftime("%B %d, %Y"),
                "created_at":     now.isoformat(),
            })
            logger.info("[Summary] Saved for %s session %s — topics: %s",
                        self.student_name, self.session_id, data.get("topics"))
        except Exception as e:
            logger.error("[Summary] MongoDB save failed: %s", e)

    def _extract_and_update_profile(self, history_snapshot: list):
        """
        Extract structured student facts (interests/struggling topics/strengths) from a
        session's conversation via Claude Haiku, then merge into student_profiles.
        Runs in a background daemon thread — any failure is logged and swallowed.
        Skipped if < 4 messages (not enough signal) or no student_id.
        """
        if not self.student_id or not history_snapshot or len(history_snapshot) < 4:
            return
        try:
            turns = history_snapshot[-20:]
            transcript_lines = []
            for turn in turns:
                role = "Child" if turn.get("role") == "user" else "Mimi"
                transcript_lines.append(f"{role}: {turn.get('content', '')[:200]}")
            transcript = "\n".join(transcript_lines)

            prompt = (
                f"You are analyzing a conversation between an AI tutor named Mimi and a child named {self.student_name}.\n"
                "Extract structured information about the child from this conversation.\n\n"
                f"Conversation:\n{transcript}\n\n"
                "Return ONLY valid JSON with these exact keys (use empty arrays/objects if no data found):\n"
                '{"interests":["list of topics the child showed interest in, max 10"],'
                '"struggling_topics":["topics the child found difficult, max 5"],'
                '"progress":{"strengths":["things the child did well, max 5"],'
                '"areas_to_improve":["areas needing improvement, max 5"]}}\n\n'
                "Only include facts clearly evidenced in the conversation. Do not infer or guess."
            )

            if not _anthropic_sdk or not self.anthropic_key:
                logger.debug("[Profile] Anthropic unavailable — skipping profile extraction")
                return

            client = _get_anthropic_singleton(self.anthropic_key)
            if not client:
                return

            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=400,
                temperature=0.1,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.content[0].text or ""
            clean = re.sub(r"```[a-z]*", "", raw).replace("```", "").strip()
            extracted = json.loads(clean)

            if not isinstance(extracted, dict):
                logger.warning("[Profile] Haiku returned non-dict for %s", self.student_name)
                return

            now = datetime.now(timezone.utc)

            interests        = [s for s in extracted.get("interests", [])                       if isinstance(s, str)][:10]
            struggling       = [s for s in extracted.get("struggling_topics", [])               if isinstance(s, str)][:5]
            strengths        = [s for s in extracted.get("progress", {}).get("strengths", [])   if isinstance(s, str)][:5]
            areas_to_improve = [s for s in extracted.get("progress", {}).get("areas_to_improve", []) if isinstance(s, str)][:5]

            update: dict = {
                "$set": {"name": self.student_name, "last_session_date": now.isoformat(), "updated_at": now.isoformat()},
                "$inc": {"total_sessions": 1},
            }
            add_to_set: dict = {}
            if interests:        add_to_set["interests"]               = {"$each": interests}
            if struggling:       add_to_set["struggling_topics"]       = {"$each": struggling}
            if strengths:        add_to_set["progress.strengths"]      = {"$each": strengths}
            if areas_to_improve: add_to_set["progress.areas_to_improve"] = {"$each": areas_to_improve}
            if add_to_set:
                update["$addToSet"] = add_to_set

            _ext_db["student_profiles"].update_one(
                {"student_id": self.student_id},
                update,
                upsert=True,
            )
            logger.info("[Profile] Updated profile for %s (interests=%d, struggling=%d)",
                        self.student_name, len(interests), len(struggling))

        except Exception as e:
            logger.warning("[Profile] Extraction failed for %s: %s", self.student_name, e)

    def get_memory_stats(self):
        """Get statistics about current conversation memory."""
        return {
            "messages_in_memory": len(self.conversation_history),
            "max_context_turns": self.max_context_turns,
            "session_id": self.session_id,
            "student_name": self.student_name,
            "memory_mode": self.memory_mode,
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
        Compact text summary of all memory tiers, injected into the system prompt.
        NOTE: working memory (recent turns of THIS session) is excluded here —
        _build_messages_with_history() already sends those as user/assistant messages.
        """
        parts = []
        # Always anchor the student's name — this survives even when profile/LTM are empty
        if self.student_name:
            parts.append(f"Student's name: {self.student_name}.")
        if self._profile_context:
            parts.append(self._profile_context)
        if self.long_term_summary:
            parts.append(f"Past sessions: {self.long_term_summary}")
        if self.topics_discussed:
            parts.append(f"Topics already discussed: {', '.join(self.topics_discussed[:15])}")
        if self._advanced_context:
            parts.append(f"Advanced context: {self._advanced_context}")
        return "\n".join(parts) if parts else "No prior memory yet — this is a fresh start."

    def _build_system_prompt(self) -> str:
        name = self.student_name or "friend"

        memory_prompt = (
            f"MEMORY RULES: Read the PAST SESSIONS block carefully before every reply. "
            f"1) If {name} asks about something from a past session, reference it warmly — "
            f"'Last time you asked about X, remember?' or 'We learned Y together!'  "
            f"2) Notice patterns in curiosity across sessions ('You love space topics!'). "
            f"3) Never re-explain basics already taught in past sessions — build on them. "
            f"4) At session START, greet them with a callback to the last session if summaries exist."
        )

        playful_prompt = (
            f"You are Mimi — {name}'s playful, magical AI learning buddy, like a fun older sister. "
            f"IMPORTANT: Always address {name} by name at least once in every response. "
            "Warm, excited, full of curiosity. Use expressive words (\"Wow!\", \"Hooray!\", \"Let's explore!\"). "
            "Use 1-2 emojis in text — they show in the chat UI. "
            "Turn learning into a tiny story or game. Celebrate correct answers. "
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

        json_format = (
            'OUTPUT FORMAT — respond with ONLY a JSON object, no text outside it:\n'
            '{"text":"<your reply>","image_search_term":"<blank or search>","youtube_search_term":"<blank or search> for kids explained","topic":"<blank or topic>"}'
        )

        table_rule = (
            "⚠️ MULTIPLICATION TABLE — HIGHEST PRIORITY OVERRIDE:\n"
            "If the user asks for ANY multiplication table ('table of 5', 'paanch ka pahada', '7 ka table', etc.), "
            "output EXACTLY this JSON structure — replace the number words for whichever number was requested:\n"
            '{"text":"Five one za five, Five two za ten, Five three za fifteen, Five four za twenty, '
            'Five five za twenty five, Five six za thirty, Five seven za thirty five, Five eight za forty, '
            f'Five nine za forty five, Five ten za fifty! Great job, {name}! 🌟",'
            '"image_search_term":"","youtube_search_term":"","topic":"multiplication"}\n'
            "STRICT RULES: number WORDS only (Five/Six/Seven…) — NEVER digits, NEVER × or =, NEVER a header line like "
            "'Here is the table of 5:', NEVER newlines inside text. Entries separated by commas. "
            "Adjust all words for the actual number requested (e.g. table of 7 → 'Seven one za seven, Seven two za fourteen…')."
        )

        prompt = (
            f"{json_format}\n\n"
            f"{memory_prompt}\n\n{playful_prompt}\n\n"
            f"Current memory context:\n{memory_context}"
            f"{realtime_block}\n\n"
            f"{table_rule}\n\n"
            f'RULES (for all other queries): Always say {name}\'s name somewhere in text. Vary openers. 1 cool fact. End with 1 question. Max 35 words in text. '
            f'Fill image_search_term AND youtube_search_term for any named thing, animal, place, or topic.\n'
            f"{media_rule}\n\n"
            f"IMPORTANT: Output ONLY the JSON object above — no explanations, no prose before or after the JSON."
        )
        return prompt, 400

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
                response_format={"type": "json_object"},
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
        start = text.find("{")
        end   = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        json_str = text[start:end + 1]
        try:
            return json.loads(json_str)
        except Exception:
            pass
        # Last resort: if JSON is truncated, try to at least extract the text field
        extracted = _try_extract_text(json_str)
        if extracted:
            return {"text": extracted, "image_search_term": "", "youtube_search_term": "", "topic": ""}
        logger.warning("Failed to parse JSON from LLM response: %s", text[:120])
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
            logger.warning("[YouTube] YOUTUBE_API_KEY not set — video search disabled")
            return None
        # Append educational suffix if not already present
        suffix = "for kids educational"
        q = search_term if any(s in search_term.lower() for s in ["for kids", "explained", "educational"]) \
            else f"{search_term} {suffix}"
        try:
            r = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params={
                    "part": "snippet", "q": q, "type": "video",
                    "safeSearch": "strict", "videoEmbeddable": "true",
                    "regionCode": "IN", "relevanceLanguage": "en",
                    "maxResults": 3, "key": api_key,
                },
                timeout=5,
            )
            if not r.ok:
                err = r.json().get("error", {})
                logger.error("[YouTube] API error %d — %s", r.status_code, err.get("message", r.text[:200]))
                return None
            for item in r.json().get("items", []):
                id_block = item.get("id", {})
                if id_block.get("kind") == "youtube#video":
                    video_id = id_block.get("videoId", "")
                    if video_id:
                        logger.info("[YouTube] Found video %s for query: %s", video_id, q)
                        return f"https://www.youtube.com/embed/{video_id}"
            logger.warning("[YouTube] No embeddable results for: %s", q)
        except Exception as e:
            logger.error("[YouTube] Request exception: %s", e)
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
                response_format={"type": "json_object"},
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
        # Never fall back to raw full_text — if JSON parse failed, use early-extracted
        # text. If that's also missing, use prose before the first '{' (strips JSON scaffold).
        if not data and not tts_text:
            brace = full_text.find("{")
            tts_text = (full_text[:brace].strip() if brace > 0 else full_text.strip()) or None
        resp_text = (data.get("text") if data else None) or tts_text or "I'm thinking, ask me again!"
        topic     = (data.get("topic") if data else "") or ""
        search    = (data.get("image_search_term") if data else "") or ""
        yt_search = (data.get("youtube_search_term") if data else "") or search or topic

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
            try:   image_url = img_fut.result(timeout=3)
            except Exception: pass
        if yt_fut:
            try:   yt_video  = yt_fut.result(timeout=6)
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
        yt_search = data.get("youtube_search_term") or search or topic

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
            try:   image_url = futures["image"].result(timeout=3)
            except Exception: pass
        if "yt" in futures:
            try:   yt_video  = futures["yt"].result(timeout=6)
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
            # ── Farewell check — skip LLM, play warm goodbye ─────────
            if self._is_farewell(user_text):
                import random
                import threading
                MOTIVATIONAL_QUOTES = [
                    "You're a star! 🌟 Keep shining bright!",
                    "Every day you learn something new – that's amazing! 🚀",
                    "You're growing smarter and smarter! See you next time! 👋",
                    "Remember, you can do anything you put your mind to! 💪",
                    "Learning is an adventure, and you're the best explorer! 🗺️",
                    "You're so curious – that's the best superpower! 🦸",
                    "Keep asking questions – that's how we learn! ❓",
                    "You made today awesome! Come back soon! 🎉",
                ]
                msg = random.choice(MOTIVATIONAL_QUOTES)
                self._add_to_history("user", user_text)
                self._add_to_history("assistant", msg)
                self.current_text   = msg
                self.current_action = "done"
                self.session_ended  = True
                logger.info("[Farewell] Detected farewell — session ending: %s", self.session_id)

                # Snapshot history NOW and generate session summary in background
                # (non-blocking — response is already built above)
                history_snapshot = list(self.conversation_history)
                threading.Thread(
                    target=self._generate_and_save_summary,
                    args=(history_snapshot,),
                    daemon=True,
                    name=f"summary-{self.session_id[:8]}",
                ).start()
                threading.Thread(
                    target=self._extract_and_update_profile,
                    args=(history_snapshot,),
                    daemon=True,
                    name=f"profile-{self.session_id[:8]}",
                ).start()

                return {"text": msg, "farewell": True, "image_url": None, "yt_video": None, "topic": "", "audio": None}

            # ── Topic list shortcut — skip LLM entirely ──────────────
            if self._is_topic_request(user_text):
                result = self._build_topic_list_response()
                self._add_to_history("user", user_text)
                self._add_to_history("assistant", result.get("text", ""))
                self.current_text   = result.get("text", "")
                self.current_action = "done"
                result["audio"]     = None
                logger.info(f"[Topics] Topic list returned — {len(result.get('topics_list', []))} topics")
                return result

            # ── Recall / Repeat shortcut — skip LLM entirely ─────────
            if self._is_recall_request(user_text):
                topic_kw = self._extract_recall_topic(user_text)
                if topic_kw and len(topic_kw) > 3:
                    # "what did I ask about planets" → search by topic (full query used for embedding)
                    q, a = self._search_qa_by_topic(topic_kw, full_query=user_text)
                else:
                    # "repeat that" / "say again" → most recent exchange
                    q, a = self._get_last_qa()

                if q and a:
                    msg = self._build_recall_response(q, a)
                else:
                    name = self.student_name or "friend"
                    msg = (
                        f"Hmm, I can't find that question yet, {name}! 🤔 "
                        "We might not have talked about it yet — ask me anything and I'll remember it! 😊"
                    )

                self._add_to_history("user", user_text)
                self._add_to_history("assistant", msg)
                self.current_text   = msg
                self.current_action = "done"
                logger.info("[Recall] Handled recall request — topic_kw=%s found=%s", topic_kw, bool(q))
                return {"text": msg, "image_url": None, "yt_video": None, "topic": "", "audio": None}

            # ── Real-time data (weather/date-time/news) for THIS turn only ──
            self._realtime_block = self._build_realtime_block(user_text)
            if self._realtime_block:
                logger.info("[Realtime] Injected: %s", self._realtime_block[:120])

            # ── Build advanced memory context for this turn ───────────────
            # Only runs when MEMORY_MODE=full is set. Default: skip (zero latency impact).
            if self.memory_router and os.getenv("MEMORY_MODE") == "full":
                try:
                    adv = self.memory_router.build_context(user_text, max_tokens=500)
                    self._advanced_context = adv.get("summary", "")
                except Exception:
                    self._advanced_context = ""
            else:
                self._advanced_context = ""

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

            # Semantic memory: embed this Q&A pair for future recall (fire-and-forget,
            # never blocks the response path — same daemon-thread pattern as summaries/profile).
            if assistant_response and self.student_id:
                import threading
                threading.Thread(
                    target=self._embed_and_store_qa,
                    args=(user_text, assistant_response, topic),
                    daemon=True,
                    name=f"embed-{self.session_id[:8]}",
                ).start()

            self.current_text   = assistant_response
            self.current_image  = result.get("image_url")
            self.current_video  = result.get("yt_video")
            self.current_action = "done"

            # ── Persist interaction to all advanced memory tiers ──────────
            # Only runs when MEMORY_MODE=full is set. Default: skip (zero latency impact).
            if self.memory_router and os.getenv("MEMORY_MODE") == "full":
                try:
                    self.memory_router.update_memories(user_text, assistant_response)
                except Exception:
                    pass

            logger.info(
                "[Memory] %d msgs | [Topics] %d topics | mode=%s",
                len(self.conversation_history), len(self.topics_discussed), self.memory_mode
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
