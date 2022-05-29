"""
ASGI config for d09 project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

from .middleware import TokenAuthMiddlewareFromPath

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'd09.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddlewareFromPath(URLRouter([
        re_path(r'^chat/(?P<room_id>[\d]+)/(?P<user_id>[\d]+)/', ...),
    ])),
})
