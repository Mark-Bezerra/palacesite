"""
ASGI config for mafia_site project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.urls import re_path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, ChannelNameRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "palacesite.settings")

django_asgi_app = get_asgi_application()

import palace.routing
from palace import consumers

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(palace.routing.websocket_urlpatterns))
        ),
        "channel": ChannelNameRouter(
            {
                "moderator": consumers.GameConsumer.as_asgi(),
            }
        ),
    }
)
