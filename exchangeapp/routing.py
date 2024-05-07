from django.urls import path
from exchangeapp import consumers
websocket_url_patterns=[
    path('ws/handleVideoChat/<str:token>',consumers.handleVideoChat.as_asgi(),name="handleVideoChat"),
]