"""
Celery App for Asynchronous Task Processing
Handles background tasks to improve response times
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Initialize Celery
redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
celery_app = Celery(
    'mimi_tasks',
    broker=redis_url,
    backend=redis_url,
    include=['tasks']  # Import tasks module
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30,  # 30 seconds max per task
    task_soft_time_limit=25,  # Soft limit at 25 seconds
    worker_prefetch_multiplier=4,  # Prefetch 4 tasks per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    result_expires=3600,  # Results expire after 1 hour
    broker_connection_retry_on_startup=True,
)

if __name__ == '__main__':
    celery_app.start()
