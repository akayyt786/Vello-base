"""
WSGI config for Own Firebase (ownfirebase) project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ownfirebase.settings')
application = get_wsgi_application()
