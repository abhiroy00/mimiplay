"""
Redis-backed session store with in-process LRU L1 cache.

Tiers:
  L1 (in-process) : OrderedDict LRU, max 20 entries — hot sessions skip Redis entirely.
                    /mimi-get polls every 2-3 s: L1 hit = zero Redis round-trips.
  L2 (Redis)      : JSON with 90-min TTL — survives restarts, shared across Gunicorn workers.
  Fallback        : plain in-memory dict with lazy GC if Redis is unavailable.

Serialization notes:
  - API keys (openai, anthropic, youtube, tavily) are NEVER stored in Redis.
    They are re-read from env vars on deserialization.
  - current_audio (base64 MP3, can be 100–500 KB) is excluded to keep payloads small.
    It regenerates on the next /mimi-get call when current_audio_text changes.
  - student_id (MongoDB ObjectId) is serialized as a plain string and restored via ObjectId().
  - memory_router (MemoryRouter instance) is not serialized; it is re-initialized lazily
    on deserialization when memory_mode == "advanced".
"""

import os
import json
import logging
import time
from collections import OrderedDict

from bson import ObjectId

logger = logging.getLogger(__name__)

try:
    import redis as _redis_lib
    _REDIS_LIB_AVAILABLE = True
except ImportError:
    _REDIS_LIB_AVAILABLE = False

# All JSON-serializable fields that should survive a worker restart or swap.
_SERIALIZED_FIELDS = [
    "session_id", "student_name", "student_age",
    "current_text", "current_image", "current_video",
    "current_audio_text", "current_action",
    "topics_discussed", "long_term_summary",
    "history_loaded", "session_ended",
    "max_context_turns", "memory_mode",
    "conversation_history",
    "_realtime_block", "_advanced_context", "_profile_context",
]


class SessionStore:
    """
    Thread-safe* session store (CPython GIL protects simple dict ops in threaded Flask).

    Usage:
        store = SessionStore(redis_url="redis://localhost:6379/0")
        store.set(session_id, session)
        session = store.get(session_id)   # L1 hit → no Redis call
        store.touch(session_id)           # reset TTL without deserializing
        store.delete(session_id)          # explicit removal on /stop-session
    """

    def __init__(self, redis_url: str = None, ttl: int = 5400, l1_max: int = 20):
        self._ttl = ttl
        self._l1_max = l1_max
        self._l1: OrderedDict = OrderedDict()   # LRU: least-recently-used at the left

        self._redis = None
        self._mode = "memory"

        if _REDIS_LIB_AVAILABLE and redis_url:
            try:
                r = _redis_lib.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                r.ping()
                self._redis = r
                self._mode = "redis"
                # Mask credentials in log output
                safe_url = redis_url.split("@")[-1] if "@" in redis_url else redis_url
                logger.info("[SessionStore] Redis backend ready (%s)", safe_url)
            except Exception as e:
                logger.warning(
                    "[SessionStore] Redis unavailable (%s) — falling back to in-memory "
                    "(sessions will not survive worker restarts)", e
                )
        else:
            if not _REDIS_LIB_AVAILABLE:
                logger.warning("[SessionStore] 'redis' package not installed — using in-memory fallback")
            else:
                logger.info("[SessionStore] REDIS_URL not set — using in-memory fallback")

        # Fallback store (also used as a write-through cache when Redis is active)
        self._mem: dict = {}
        self._mem_ts: dict = {}      # session_id → last-access float
        self._last_mem_gc: float = 0.0

    # ── Public API ─────────────────────────────────────────────────────────────

    def get(self, session_id: str):
        """
        Return MimiLLMSession or None.
        Order: L1 (in-process) → Redis → None.
        """
        # L1 hit — same worker, hot session, no I/O
        if session_id in self._l1:
            self._l1.move_to_end(session_id)
            return self._l1[session_id]

        if self._mode == "redis":
            try:
                raw = self._redis.get(f"mimi:session:{session_id}")
            except Exception as e:
                logger.error("[SessionStore] Redis get failed: %s", e)
                # Degrade gracefully to in-memory fallback
                return self._mem.get(session_id)
            if not raw:
                return None
            session = self._deserialize(raw)
            if session:
                self._l1_put(session_id, session)
            return session
        else:
            self._maybe_mem_gc()
            session = self._mem.get(session_id)
            if session:
                self._mem_ts[session_id] = time.time()
            return session

    def set(self, session_id: str, session, ttl: int = None):
        """
        Persist session to Redis (if available) and update L1.
        call after every mutation that must survive a worker swap.
        """
        ttl = ttl or self._ttl

        if self._mode == "redis":
            try:
                self._redis.setex(f"mimi:session:{session_id}", ttl, self._serialize(session))
            except Exception as e:
                logger.error("[SessionStore] Redis set failed: %s", e)

        # Write-through: L1 always has the latest object reference
        self._l1_put(session_id, session)

        # Keep fallback mem in sync (essential in memory mode, harmless in redis mode)
        self._mem[session_id] = session
        self._mem_ts[session_id] = time.time()

    def delete(self, session_id: str):
        """Remove session from all tiers (called on /stop-session)."""
        self._l1.pop(session_id, None)
        if self._mode == "redis":
            try:
                self._redis.delete(f"mimi:session:{session_id}")
            except Exception as e:
                logger.error("[SessionStore] Redis delete failed: %s", e)
        self._mem.pop(session_id, None)
        self._mem_ts.pop(session_id, None)

    def touch(self, session_id: str, ttl: int = None):
        """
        Reset Redis TTL without serializing the session object.
        Used by /mimi-get poll — cheap, no deserialization.
        """
        ttl = ttl or self._ttl
        if self._mode == "redis":
            try:
                self._redis.expire(f"mimi:session:{session_id}", ttl)
            except Exception as e:
                logger.warning("[SessionStore] Redis touch failed: %s", e)
        else:
            if session_id in self._mem:
                self._mem_ts[session_id] = time.time()

    # ── L1 helpers ─────────────────────────────────────────────────────────────

    def _l1_put(self, session_id: str, session):
        if session_id in self._l1:
            self._l1.move_to_end(session_id)
        self._l1[session_id] = session
        while len(self._l1) > self._l1_max:
            self._l1.popitem(last=False)  # evict least-recently-used

    # ── Fallback GC (memory mode only) ─────────────────────────────────────────

    def _maybe_mem_gc(self):
        """Rate-limited scan for stale entries in in-memory fallback (runs at most every 5 min)."""
        now = time.time()
        if now - self._last_mem_gc < 300:
            return
        self._last_mem_gc = now
        stale = [sid for sid, ts in list(self._mem_ts.items()) if now - ts > self._ttl]
        for sid in stale:
            self._mem.pop(sid, None)
            self._mem_ts.pop(sid, None)
        if stale:
            logger.info("[SessionStore] Memory GC evicted %d stale session(s)", len(stale))

    # ── Serialization ───────────────────────────────────────────────────────────

    def _serialize(self, session) -> str:
        d = {field: getattr(session, field, None) for field in _SERIALIZED_FIELDS}
        # ObjectId is not JSON-serializable — store as plain string
        d["student_id"] = str(session.student_id) if getattr(session, "student_id", None) else None
        # current_audio intentionally excluded: base64 payload is large and regenerates cheaply
        return json.dumps(d, default=str)

    def _deserialize(self, raw: str):
        try:
            d = json.loads(raw)
        except Exception as e:
            logger.error("[SessionStore] JSON parse failed on deserialization: %s", e)
            return None

        try:
            # Lazy import avoids circular-import issues at module load time
            from mimi_llm_session import MimiLLMSession

            sid_str = d.get("student_id")
            student_id = ObjectId(sid_str) if sid_str else None

            # Bypass __init__ so we can set every attribute exactly as serialized
            session = MimiLLMSession.__new__(MimiLLMSession)

            # API keys: never stored — always sourced from env at restore time
            session.openai_key    = os.environ.get("OPENAI_API_KEY", "")
            session.anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
            session.youtube_key   = os.environ.get("YOUTUBE_API_KEY", "")
            session.tavily_key    = os.environ.get("TAVILY_API_KEY", "")
            session.timezone      = os.environ.get("MIMI_TIMEZONE", "Asia/Kolkata")

            session.student_id   = student_id
            session.student_name = d.get("student_name", "")
            session.student_age  = d.get("student_age", 10)
            session.session_id   = d.get("session_id", "")

            session.current_text       = d.get("current_text")
            session.current_image      = d.get("current_image")
            session.current_video      = d.get("current_video")
            session.current_action     = d.get("current_action", "idle")
            session.current_audio      = None           # never stored — will regenerate
            session.current_audio_text = d.get("current_audio_text")

            session.conversation_history = d.get("conversation_history", [])
            session.topics_discussed     = d.get("topics_discussed", [])
            session.long_term_summary    = d.get("long_term_summary", "")
            session.history_loaded       = bool(d.get("history_loaded", False))
            session.session_ended        = bool(d.get("session_ended", False))
            session.max_context_turns    = int(d.get("max_context_turns", 3))
            session.memory_mode          = d.get("memory_mode", "basic")

            session._realtime_block   = d.get("_realtime_block", "")
            session._advanced_context = d.get("_advanced_context", "")
            session._profile_context  = d.get("_profile_context", "")

            # MemoryRouter is not serializable — reinitialize if the session was using it
            session.memory_router = None
            if session.memory_mode == "advanced" and student_id:
                try:
                    from memory_system import MemoryRouter, ADVANCED_MEMORY_AVAILABLE
                    if ADVANCED_MEMORY_AVAILABLE:
                        session.memory_router = MemoryRouter(str(student_id), session.session_id)
                        logger.debug("[SessionStore] MemoryRouter reinitialized for %s", session.student_name)
                except Exception as e:
                    logger.warning("[SessionStore] MemoryRouter reinit failed: %s", e)

            logger.debug("[SessionStore] Deserialized session=%s student=%s",
                         session.session_id, session.student_name)
            return session

        except Exception as e:
            logger.error("[SessionStore] Deserialization failed: %s", e, exc_info=True)
            return None
