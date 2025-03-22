import os
from celery import Celery
from celery.schedules import crontab

# 设置默认Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospitalLane.settings.local')

app = Celery('hospitalLane')

# 使用Django的settings文件配置Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动从所有已注册的Django应用中加载任务
app.autodiscover_tasks()

# 配置定时任务
app.conf.beat_schedule = {
    'update-queue-wait-times': {
        'task': 'navigation.tasks.update_queue_wait_times',
        'schedule': 120.0,  # 每2分钟执行一次，使用新的等待时间计算算法
    },
    'check-delayed-queues': {
        'task': 'navigation.tasks.check_delayed_queues',
        'schedule': 300.0,  # 每5分钟执行一次
    },
    'clean-expired-queues': {
        'task': 'navigation.tasks.clean_expired_queues',
        'schedule': crontab(hour=0, minute=0),  # 每天凌晨执行
    },
    'update-department-statistics': {
        'task': 'navigation.tasks.update_department_statistics',
        'schedule': 900.0,  # 每15分钟执行一次
    },
    'retry-failed-notifications': {
        'task': 'navigation.tasks.retry_failed_notifications',
        'schedule': 600.0,  # 每10分钟执行一次
    },
    'clean-old-notifications': {
        'task': 'navigation.tasks.clean_old_notifications',
        'schedule': crontab(hour=1, minute=0),  # 每天凌晨1点执行
    },
    'update-notification-stats': {
        'task': 'navigation.tasks.update_notification_stats',
        'schedule': 3600.0,  # 每小时执行一次
    },
    # Prophet模型训练计划
    'train-prophet-models': {
        'task': 'navigation.ml.tasks.train_prophet_models',
        'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点训练模型
        'options': {'expires': 3600}  # 过期时间设为1小时
    },
}

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 