"""
Celery configuration for Own Firebase.
"""

import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ownfirebase.settings')

app = Celery('ownfirebase')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()

# Default routing
app.conf.task_default_queue = 'default'
app.conf.task_queues = {
    'default': {'exchange': 'default', 'routing_key': 'default'},
    'high_priority': {'exchange': 'high_priority', 'routing_key': 'high_priority'},
    'low_priority': {'exchange': 'low_priority', 'routing_key': 'low_priority'},
}

# Beat schedule (Phase 1 MVP: placeholder for scheduled tasks)
app.conf.beat_schedule = {
    # Example: send periodic heartbeat (Phase 2+)
    # 'heartbeat': {
    #     'task': 'tasks.heartbeat',
    #     'schedule': crontab(minute='*/5'),
    # },
}

@app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f'Request: {self.request!r}')
