"""
ASGI config for smartfindAPI project.

It exposes the ASGI callable as a module-plan variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smartfindAPI.settings.dev")

application = get_asgi_application()
