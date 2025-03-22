from celery import shared_task
from django.utils import timezone
from django.db.models import F, Q, Avg
from django.core.cache import cache
from datetime import timedelta
import logging

from .models import Queue, Department, NotificationTemplate, NotificationStats
from .utils.notifications import send_notification_with_template, broadcast_department_notification

logger = logging.getLogger(__name__)

@shared_task
def update_queue_wait_times():
    """更新所有等待中队列的预计等待时间"""
    try:
        # 使用新的算法计算所有等待中队列的等待时间
        waiting_queues = Queue.objects.filter(status='waiting')
        total_count = waiting_queues.count()
        
        if total_count == 0:
            logger.info("当前没有等待中的队列，无需更新等待时间")
            return {"status": "success", "message": "当前没有等待中的队列", "updated_count": 0, "total_count": 0}
        
        logger.info(f"开始更新 {total_count} 个等待中队列的预计等待时间")
        
        updated_count = 0
        notification_count = 0
        
        for queue in waiting_queues:
            old_time = queue.estimated_wait_time
            # 使用集成了Prophet的算法计算预计等待时间
            new_time = queue.estimate_initial_wait_time()
            
            # 如果等待时间发生变化，更新记录
            if old_time != new_time:
                queue.estimated_wait_time = new_time
                queue.save(update_fields=['estimated_wait_time'])
                updated_count += 1
            
                # 如果等待时间显著变化（超过5分钟），发送通知
                if abs(old_time - new_time) > 5:
                    try:
                        send_notification.delay(
                            template_code='queue_wait_time_update',
                            recipient_id=queue.patient.id,
                            context={
                                'wait_time': new_time,
                                'queue_number': queue.queue_number,
                                'department': queue.department.name,
                                'examination': queue.examination.name
                            }
                        )
                        notification_count += 1
                    except Exception as notify_err:
                        logger.warning(f"发送等待时间更新通知失败: {str(notify_err)}")
        
        success_msg = f"成功更新 {updated_count}/{total_count} 个队列的等待时间，发送了 {notification_count} 个通知"
        logger.info(success_msg)
        logger.info(f"等待时间更新完成，成功率: {(updated_count/total_count)*100 if total_count > 0 else 0:.1f}%")
        
        return {
            "status": "success", 
            "message": success_msg,
            "updated_count": updated_count,
            "total_count": total_count,
            "notification_count": notification_count
        }
        
    except Exception as e:
        error_msg = f"更新队列等待时间出错: {str(e)}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}

@shared_task
def check_delayed_queues():
    """检查并处理延迟的队列"""
    try:
        # 找出所有超时的队列
        current_time = timezone.now()
        delayed_queues = Queue.objects.filter(
            status='waiting'
        ).exclude(
            estimated_wait_time=None
        ).annotate(
            expected_end_time=F('enter_time') + timedelta(minutes=15)  # 默认15分钟
        ).filter(
            expected_end_time__lt=current_time
        )
        
        delayed_count = 0
        for queue in delayed_queues:
            # 发送延迟通知给患者
            send_notification.delay(
                template_code='queue_delayed',
                recipient_id=queue.patient.id,
                context={
                    'examination_name': queue.examination.name,
                    'queue_number': queue.queue_number
                }
            )
            
            # 通知科室工作人员
            broadcast_department_notification(
                department=queue.department,
                template_code='queue_delayed_staff',
                context={
                    'queue_number': queue.queue_number,
                    'examination_name': queue.examination.name,
                    'patient_name': queue.patient.name
                }
            )
            delayed_count += 1
        
        logger.info(f"Processed {delayed_count} delayed queues")
        return f"Processed {delayed_count} delayed queues"
        
    except Exception as e:
        logger.error(f"Error checking delayed queues: {str(e)}")
        raise

@shared_task
def clean_expired_queues():
    """清理过期队列"""
    try:
        yesterday = timezone.now() - timedelta(days=1)
        
        # 自动取消超过24小时的等待队列
        expired_queues = Queue.objects.filter(
            status='waiting',
            enter_time__lt=yesterday
        )
        
        for queue in expired_queues:
            queue.update_status('cancelled')
            send_notification.delay(
                template_code='queue_expired',
                recipient_id=queue.patient.id,
                context={
                    'examination_name': queue.examination.name,
                    'queue_number': queue.queue_number
                }
            )
        
        expired_count = expired_queues.count()
        logger.info(f"Cleaned {expired_count} expired queues")
        return f"Cleaned {expired_count} expired queues"
        
    except Exception as e:
        logger.error(f"Error cleaning expired queues: {str(e)}")
        raise

@shared_task
def update_department_statistics():
    """更新科室统计数据"""
    try:
        departments = Department.objects.all()
        for dept in departments:
            # 计算今日总接诊数
            today = timezone.now().date()
            total_queues = Queue.objects.filter(
                department=dept,
                created_at__date=today
            ).count()
            
            # 计算平均等待时间
            completed_queues = Queue.objects.filter(
                department=dept,
                status='completed',
                end_time__date=today
            )
            avg_wait_time = completed_queues.aggregate(
                avg_time=Avg('actual_wait_time')
            )['avg_time'] or 0
            
            # 更新缓存
            cache.set(
                f'dept_stats_{dept.id}_{today}',
                {
                    'total_queues': total_queues,
                    'avg_wait_time': round(avg_wait_time, 1),
                    'updated_at': timezone.now()
                },
                timeout=86400  # 24小时
            )
        
        logger.info(f"Updated statistics for {departments.count()} departments")
        return f"Updated department statistics"
        
    except Exception as e:
        logger.error(f"Error updating department statistics: {str(e)}")
        raise

@shared_task(bind=True, max_retries=3)
def send_notification(self, template_code, recipient_id, context, force=False):
    """
    异步发送通知任务
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        recipient = User.objects.get(id=recipient_id)
        
        result = send_notification_with_template(
            recipient=recipient,
            template_code=template_code,
            context=context,
            force=force
        )
        return result
    except Exception as exc:
        logger.error(f'发送通知失败: {str(exc)}', exc_info=True)
        # 使用指数退避策略重试
        retry_in = (2 ** self.request.retries) * 60  # 1分钟, 2分钟, 4分钟
        raise self.retry(exc=exc, countdown=retry_in)

@shared_task
def retry_failed_notifications():
    """
    重试失败的通知
    """
    from .models import NotificationStats
    
    # 获取最近24小时内失败的通知
    yesterday = timezone.now() - timedelta(days=1)
    failed_stats = NotificationStats.objects.filter(
        date__gte=yesterday,
        fail_count__gt=0
    ).select_related('template')
    
    retry_count = 0
    for stat in failed_stats:
        template = stat.template
        # 从缓存中获取失败的通知
        failed_key = f'failed_notifications_{template.code}_{stat.date.isoformat()}'
        failed_notifications = cache.get(failed_key, [])
        
        for notification in failed_notifications:
            try:
                send_notification.delay(
                    template_code=template.code,
                    recipient_id=notification['recipient_id'],
                    context=notification['context'],
                    force=True
                )
                retry_count += 1
            except Exception as e:
                logger.error(f'重试通知失败: {str(e)}', exc_info=True)
        
        # 清除已处理的失败通知
        cache.delete(failed_key)
    
    logger.info(f'重试了 {retry_count} 条失败的通知')
    return f'Retried {retry_count} failed notifications'

@shared_task
def clean_old_notifications():
    """
    清理旧的通知数据
    """
    from django.core.cache import cache
    from .utils.notifications import get_notifications
    
    # 清理7天前的通知统计数据
    week_ago = timezone.now() - timedelta(days=7)
    NotificationStats.objects.filter(date__lt=week_ago).delete()
    
    # 这里可以添加其他清理逻辑，比如清理缓存中的旧通知等

@shared_task
def update_notification_stats():
    """
    更新通知统计数据
    """
    templates = NotificationTemplate.objects.filter(is_active=True)
    today = timezone.now().date()
    
    for template in templates:
        for channel in template.channel_types:
            stats, _ = NotificationStats.objects.get_or_create(
                template=template,
                channel=channel,
                date=today
            )
            # 这里可以添加更多统计逻辑 