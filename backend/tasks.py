"""
Celery Tasks for Background Processing
Offloads heavy operations to improve response time
"""

import logging
import requests
from celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='tasks.fetch_wikimedia_image', bind=True, max_retries=2)
def fetch_wikimedia_image(self, search_term):
    """
    Async task to fetch Wikimedia image
    Runs in background to not block main response
    """
    try:
        r = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": search_term,
                "gsrlimit": 5,
                "gsrnamespace": 6,
                "prop": "imageinfo",
                "iiprop": "url",
                "format": "json",
            },
            headers={"User-Agent": "MimiBot/1.0"},
            timeout=5,
        )
        r.raise_for_status()
        
        for page in r.json().get("query", {}).get("pages", {}).values():
            url = page.get("imageinfo", [{}])[0].get("url")
            if url:
                return {"success": True, "url": url}
        
        return {"success": False, "url": None}
    except Exception as e:
        logger.error(f"Wikimedia fetch failed: {e}")
        # Retry with exponential backoff
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except self.MaxRetriesExceededError:
            return {"success": False, "url": None, "error": str(e)}


@celery_app.task(name='tasks.fetch_youtube_video', bind=True, max_retries=2)
def fetch_youtube_video(self, search_term, api_key):
    """
    Async task to fetch YouTube video
    Runs in background to not block main response
    """
    try:
        # Add educational suffix if not present
        suffix = "for kids educational"
        q = search_term if any(s in search_term.lower() for s in ["for kids", "explained", "educational"]) \
            else f"{search_term} {suffix}"
        
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={
                "part": "snippet",
                "q": q,
                "type": "video",
                "safeSearch": "strict",
                "videoEmbeddable": "true",
                "maxResults": 3,
                "key": api_key,
            },
            timeout=5,
        )
        r.raise_for_status()
        
        for item in r.json().get("items", []):
            id_block = item.get("id", {})
            if id_block.get("kind") == "youtube#video":
                video_id = id_block.get("videoId", "")
                if video_id:
                    return {"success": True, "url": f"https://www.youtube.com/embed/{video_id}"}
        
        return {"success": False, "url": None}
    except Exception as e:
        logger.error(f"YouTube fetch failed: {e}")
        try:
            raise self.retry(exc=e, countdown=2 ** self.request.retries)
        except self.MaxRetriesExceededError:
            return {"success": False, "url": None, "error": str(e)}


@celery_app.task(name='tasks.update_memory_async')
def update_memory_async(student_id, session_id, user_message, assistant_response, metadata):
    """
    Async task to update advanced memory system
    Runs in background after response is sent
    """
    try:
        from memory_system import MemoryRouter
        
        memory = MemoryRouter(student_id, session_id)
        memory.update_memories(user_message, assistant_response, metadata)
        
        return {"success": True, "message": "Memory updated"}
    except Exception as e:
        logger.error(f"Memory update failed: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name='tasks.save_chat_to_db')
def save_chat_to_db(session_id, student_id, student_name, message_obj):
    """
    Async task to save chat to database
    Runs in background to not block response
    """
    try:
        from pymongo import MongoClient
        from datetime import datetime
        import os
        
        mongo_uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
        client = MongoClient(mongo_uri)
        db = client["AlexiDB"]
        mimi_chats = db["mimi_chats"]
        
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        existing = mimi_chats.find_one({"session_id": session_id, "date": today})
        
        if existing:
            mimi_chats.update_one(
                {"_id": existing["_id"]},
                {
                    "$push": {"messages": message_obj},
                    "$set": {"updated_at": now.isoformat()},
                    "$inc": {"total_msgs": 1}
                }
            )
        else:
            from bson import ObjectId
            try:
                sid_oid = ObjectId(student_id) if student_id else None
            except:
                sid_oid = None
            
            mimi_chats.insert_one({
                "student_id": sid_oid,
                "student_name": student_name,
                "session_id": session_id,
                "messages": [message_obj],
                "date": today,
                "started_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "total_msgs": 1
            })
        
        return {"success": True}
    except Exception as e:
        logger.error(f"DB save failed: {e}")
        return {"success": False, "error": str(e)}


@celery_app.task(name='tasks.generate_tts_audio')
def generate_tts_audio(text):
    """
    Async task to generate TTS audio
    Can be cached in Redis for repeated phrases
    """
    try:
        import asyncio
        import edge_tts
        import tempfile
        import base64
        import os
        
        if not text:
            return {"success": False, "audio": ""}
        
        async def generate(text, path):
            communicate = edge_tts.Communicate(
                text, 
                voice="en-IN-NeerjaExpressiveNeural", 
                rate="-10%", 
                pitch="+15Hz"
            )
            await communicate.save(path)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as f:
            tmp_path = f.name
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(generate(text, tmp_path))
        finally:
            loop.close()
        
        with open(tmp_path, 'rb') as f:
            audio_data = base64.b64encode(f.read()).decode()
        
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        
        return {"success": True, "audio": audio_data}
    except Exception as e:
        logger.error(f"TTS generation failed: {e}")
        return {"success": False, "audio": "", "error": str(e)}
