import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospitalLane.settings')
django.setup()

# 导入必要的组件
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.generic.websocket import WebsocketConsumer
from django.urls import path

# 导入消费者
from navigation.consumers import QueueConsumer

# 定义WebSocket路由
websocket_urlpatterns = [
    path('ws/queue_updates/', QueueConsumer.as_asgi()),
]

# 配置ASGI应用
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": URLRouter(websocket_urlpatterns),
}) 