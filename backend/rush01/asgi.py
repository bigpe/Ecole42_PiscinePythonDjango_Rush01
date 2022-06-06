"""
ASGI config for d09 project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rush01.settings')

import django

django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

from .middleware import AuthMiddlewareFromPath

from ws.notifications import NotificationsConsumer
from ws.chat import ChatConsumer

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareFromPath(URLRouter([
        re_path(r'^notifications/(?P<user_id>[\d]+)/', NotificationsConsumer.as_asgi()),
        re_path(r'^chat/(?P<user_id>[\d]+)/', ChatConsumer.as_asgi()),
    ])),
})
