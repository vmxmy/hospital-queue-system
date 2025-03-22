import threading
from django.utils.deprecation import MiddlewareMixin
import time
import logging
import json
from django.http import JsonResponse
from django.urls import resolve

logger = logging.getLogger(__name__)

# 保存当前请求的线程本地存储
_thread_locals = threading.local()

def get_current_request():
    """获取当前请求"""
    return getattr(_thread_locals, 'request', None)

def get_current_user():
    """获取当前用户"""
    request = get_current_request()
    if request and hasattr(request, 'user'):
        return request.user
    return None

class ThreadLocalMiddleware(MiddlewareMixin):
    """线程本地存储中间件，用于在当前线程中存储请求对象"""
    
    def process_request(self, request):
        _thread_locals.request = request
        return None
        
    def process_response(self, request, response):
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
        return response

class RequestLogMiddleware(MiddlewareMixin):
    """请求日志中间件，记录请求和响应信息"""
    
    def process_request(self, request):
        request.start_time = time.time()
        return None
        
    def process_response(self, request, response):
        if not hasattr(request, 'start_time'):
            return response
            
        # 计算请求处理时间
        duration = time.time() - request.start_time
        
        # 获取请求路径和方法
        path = request.path
        method = request.method
        
        # 获取用户信息
        user = getattr(request, 'user', None)
        user_id = user.id if user and user.is_authenticated else None
        
        # 获取响应状态码
        status_code = getattr(response, 'status_code', None)
        
        # 记录详细信息到DEBUG级别
        logger.debug(
            f"Request: {method} {path} - User: {user_id} - "
            f"Duration: {duration:.2f}s - Status: {status_code}"
        )
        
        # 如果请求时间超过1秒，记录为警告
        if duration > 1.0:
            logger.warning(
                f"Slow request: {method} {path} - "
                f"Duration: {duration:.2f}s - Status: {status_code}"
            )
            
        return response

class APIExceptionMiddleware(MiddlewareMixin):
    """API异常处理中间件，捕获API请求中的异常并返回JSON响应"""
    
    def process_exception(self, request, exception):
        # 仅处理API请求
        if not request.path.startswith('/api/'):
            return None
            
        # 记录异常
        logger.exception(f"API异常: {request.path} - {str(exception)}")
        
        # 返回JSON格式的错误响应
        return JsonResponse({
            'code': 500,
            'message': '服务器内部错误',
            'detail': str(exception)
        }, status=500) 