import os
from celery import Celery
from celery.schedules import crontab

# 设置默认 Django 配置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')

# 创建 Celery 实例
app = Celery('hospital_queue')

# 使用 Django 的配置文件配置 Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现各个应用下的 tasks.py 文件
app.autodiscover_tasks()

# 配置定时任务
app.conf.beat_schedule = {
    'update-queue-wait-times': {
        'task': 'navigation.tasks.update_queue_wait_times',
        'schedule': crontab(minute='*/5'),  # 每5分钟执行一次
    },
    'check-delayed-queues': {
        'task': 'navigation.tasks.check_delayed_queues',
        'schedule': crontab(minute='*/3'),  # 每3分钟执行一次
    },
    'clean-expired-queues': {
        'task': 'navigation.tasks.clean_expired_queues',
        'schedule': crontab(hour='0', minute='0'),  # 每天零点执行
    },
} 