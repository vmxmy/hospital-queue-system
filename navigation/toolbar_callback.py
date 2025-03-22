from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def show_toolbar(request):
    """
    决定是否显示Debug Toolbar的回调函数
    """
    try:
        # 如果不是DEBUG模式，不显示
        if not settings.DEBUG:
            return False
            
        # 使用请求属性判断
        if hasattr(request, '_debug_toolbar_enable') and request._debug_toolbar_enable is False:
            return False
            
        if hasattr(request, '_show_toolbar'):
            return request._show_toolbar
            
        # 如果不在INTERNAL_IPS中，不显示
        if request.META.get('REMOTE_ADDR') not in settings.INTERNAL_IPS:
            return settings.DEBUG  # 在开发环境中仍然显示
            
        # 不在API请求和AJAX请求中显示
        if (request.path.startswith(('/api/', '/ml_', '/__debug__/')) or 
            request.headers.get('x-requested-with') == 'XMLHttpRequest'):
            return False
        
        # 不在静态文件中显示
        if request.path.startswith(('/static/', '/media/')):
            return False
            
        # 设置toolbar属性
        request.toolbar = True
            
        return True
    except Exception as e:
        logger.exception(f"Debug Toolbar show_toolbar error: {e}")
        return False
