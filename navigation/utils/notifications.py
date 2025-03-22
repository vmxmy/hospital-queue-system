import logging
import json
from django.utils import timezone
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
import time
from datetime import timedelta

from ..models.notification_template import NotificationTemplate
from ..models.notification_stats import NotificationStats

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

class NotificationRateLimitExceeded(Exception):
    pass

def check_notification_frequency(recipient_id, template_code, channel):
    """
    检查通知发送频率是否超限
    """
    cache_key = f'notification_frequency_{recipient_id}_{template_code}_{channel}'
    last_sent = cache.get(cache_key)
    
    if last_sent:
        # 获取频率限制配置
        limits = getattr(settings, 'NOTIFICATION_RATE_LIMITS', {
            'websocket': 10,  # 10秒
            'sms': 60,       # 1分钟
            'wechat': 300    # 5分钟
        })
        
        limit = limits.get(channel, 60)  # 默认1分钟
        if (timezone.now() - last_sent).total_seconds() < limit:
            return False
    
    # 更新最后发送时间
    cache.set(cache_key, timezone.now(), timeout=86400)  # 24小时过期
    return True

def send_with_retry(func, *args, max_retries=3, **kwargs):
    """
    通知发送重试装饰器
    """
    last_error = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            if attempt == max_retries - 1:
                logger.error(f'通知发送最终失败: {str(e)}', exc_info=True)
                raise
            
            # 指数退避重试
            wait_time = (2 ** attempt) + 1
            logger.warning(f'通知发送失败，{wait_time}秒后重试: {str(e)}')
            time.sleep(wait_time)
    
    raise last_error

def send_notification_with_template(recipient, template_code, context, force=False):
    """
    使用模板发送通知
    """
    try:
        template = NotificationTemplate.objects.get(code=template_code, is_active=True)
    except NotificationTemplate.DoesNotExist:
        logger.error(f'通知模板不存在: {template_code}')
        raise ValueError(f'通知模板不存在: {template_code}')

    try:
        rendered = template.render(context)
    except Exception as e:
        logger.error(f'模板渲染失败: {str(e)}')
        raise

    notification_id = f"{int(time.time())}_{recipient.id}"
    
    for channel in rendered['channel_types']:
        if not force and not check_notification_frequency(recipient.id, template_code, channel):
            logger.warning(f'通知发送频率超限: {template_code} -> {recipient.id} via {channel}')
            raise NotificationRateLimitExceeded(f'通知发送频率超限: {channel}')
        
        try:
            if channel == 'websocket':
                send_with_retry(
                    send_websocket_notification,
                    recipient=recipient,
                    notification_id=notification_id,
                    title=rendered['title'],
                    content=rendered['content']
                )
            elif channel == 'sms':
                from ..tasks import send_sms_notification
                send_sms_notification.delay(
                    recipient_id=recipient.id,
                    template_code=template.sms_template_code,
                    params=context
                )
            elif channel == 'wechat':
                from ..tasks import send_wechat_notification
                send_wechat_notification.delay(
                    recipient_id=recipient.id,
                    template_id=template.wechat_template_id,
                    data=context
                )
            
            NotificationStats.record_sent(template, channel, success=True)
            
        except Exception as e:
            logger.error(f'通知发送失败: {str(e)}', exc_info=True)
            NotificationStats.record_sent(template, channel, success=False)
            raise

def send_websocket_notification(recipient, notification_id, title, content):
    """
    发送WebSocket通知
    """
    try:
        # 获取接收者的通知频道
        recipient_channel = f"notifications_{recipient.id}"
        
        notification_data = {
            'type': 'notification.message',
            'notification_id': notification_id,
            'title': title,
            'content': content,
            'timestamp': timezone.now().isoformat()
        }
        
        async_to_sync(channel_layer.group_send)(
            recipient_channel,
            notification_data
        )
    except Exception as e:
        logger.error(f'WebSocket通知发送失败: {str(e)}', exc_info=True)
        raise

def send_sms_notification(recipient, template_code, params):
    """
    发送短信通知
    TODO: 实现具体的短信发送逻辑
    """
    # 这里添加实际的短信发送实现
    pass

def send_wechat_notification(recipient, template_id, data):
    """
    发送微信通知
    TODO: 实现具体的微信通知发送逻辑
    """
    # 这里添加实际的微信通知发送实现
    pass

def get_notifications(recipient, unread_only=False):
    """
    获取接收者的通知列表
    
    Args:
        recipient: 接收者（患者或科室）
        unread_only: 是否只返回未读通知
    """
    try:
        if hasattr(recipient, 'id'):
            # 确定接收者类型
            recipient_type = (
                'patient' if hasattr(recipient, 'medical_record_number')
                else 'staff'
            )
            
            cache_key = f'notifications_{recipient_type}_{recipient.id}'
            notifications = cache.get(cache_key) or []
            
            if unread_only:
                notifications = [n for n in notifications if not n.get('read')]
            
            return notifications
            
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return []

def mark_notifications_read(recipient, notification_ids=None):
    """
    标记通知为已读
    
    Args:
        recipient: 接收者（患者或科室）
        notification_ids: 要标记的通知ID列表，None表示全部标记
    """
    try:
        if hasattr(recipient, 'id'):
            # 确定接收者类型
            recipient_type = (
                'patient' if hasattr(recipient, 'medical_record_number')
                else 'staff'
            )
            
            cache_key = f'notifications_{recipient_type}_{recipient.id}'
            notifications = cache.get(cache_key) or []
            
            updated = False
            for notification in notifications:
                if (notification_ids is None or 
                    notification.get('id') in notification_ids):
                    notification['read'] = True
                    updated = True
            
            if updated:
                cache.set(cache_key, notifications, timeout=86400)
                
    except Exception as e:
        logger.error(f"Error marking notifications as read: {str(e)}")

def clear_notifications(recipient):
    """清除接收者的通知列表"""
    try:
        if hasattr(recipient, 'id'):
            # 确定接收者类型
            recipient_type = (
                'patient' if hasattr(recipient, 'medical_record_number')
                else 'staff'
            )
            
            cache_key = f'notifications_{recipient_type}_{recipient.id}'
            cache.delete(cache_key)
            
    except Exception as e:
        logger.error(f"Error clearing notifications: {str(e)}")

def broadcast_department_notification(department, template_code, context):
    """
    向科室所有人员发送通知
    """
    from ..tasks import send_notification
    
    staff_members = department.staff_members.filter(is_active=True)
    
    for staff in staff_members:
        try:
            send_notification.delay(
                template_code=template_code,
                recipient_id=staff.id,
                context=context
            )
        except Exception as e:
            logger.error(f'向科室成员发送通知失败: {staff.id} - {str(e)}')

def send_queue_update(queue, template_code, context):
    """
    发送队列更新通知
    """
    from ..tasks import send_notification
    
    try:
        send_notification.delay(
            template_code=template_code,
            recipient_id=queue.patient.id,
            context=context
        )
    except Exception as e:
        logger.error(f'发送队列更新通知失败: {queue.id} - {str(e)}') 