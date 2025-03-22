from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from navigation.views import index

urlpatterns = [
    path('', index, name='index'),
    path('admin/', admin.site.urls),
    path('api/', include('navigation.urls')),
]

# 添加WebSocket URL注释
# WebSocket连接由Channels处理，在asgi.py和routing.py中配置
# ws://host/ws/queue_updates/

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # 添加 Django Debug Toolbar URL
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ] 