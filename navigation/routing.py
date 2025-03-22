from django.urls import re_path
from . import consumers

# 修正WebSocket路由，确保URL模式正确
websocket_urlpatterns = [
    # 使用简单的路径模式，不使用起始^字符，以便更好地匹配
    re_path(r'ws/queue_updates/$', consumers.QueueConsumer.as_asgi()),
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/queue/(?P<queue_id>\d+)/$', consumers.QueueStatusConsumer.as_asgi()),
] 