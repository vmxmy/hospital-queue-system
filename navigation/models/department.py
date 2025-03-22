from django.db import models
from django.core.validators import MinValueValidator


class Department(models.Model):
    """科室模型"""
    
    name = models.CharField('科室名称', max_length=100)
    code = models.CharField('科室代码', max_length=20, unique=True)
    description = models.TextField('科室描述', blank=True)
    location = models.CharField('位置', max_length=200)
    floor = models.CharField('楼层', max_length=20)
    building = models.CharField('建筑', max_length=100)
    contact_phone = models.CharField('联系电话', max_length=20)
    operating_hours = models.CharField(
        '运营时间',
        max_length=100,
        help_text='例如: 08:00-17:00'
    )
    max_daily_patients = models.IntegerField(
        '每日最大接诊量',
        null=True,
        blank=True
    )
    average_service_time = models.IntegerField(
        '平均服务时间(分钟)',
        help_text='用于估算等待时间'
    )
    is_active = models.BooleanField('是否启用', default=True)
    notes = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '科室'
        verbose_name_plural = '科室'
        ordering = ['name']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return self.name

    def get_current_queue_length(self):
        """获取当前等待队列长度"""
        return self.queue_set.filter(status='waiting').count()

    def get_average_wait_time(self):
        """计算平均等待时间（分钟）"""
        from django.db.models import Avg
        from django.utils import timezone
        from datetime import timedelta

        # 获取过去24小时内完成的队列
        yesterday = timezone.now() - timedelta(days=1)
        completed_queues = self.queue_set.filter(
            status='completed',
            end_time__gte=yesterday
        )
        avg_wait_time = completed_queues.aggregate(
            Avg('actual_wait_time')
        )['actual_wait_time__avg']
        
        return round(avg_wait_time) if avg_wait_time else self.average_service_time

    def is_open(self):
        """检查科室是否在运营时间内"""
        from datetime import datetime
        current_time = datetime.now().time()
        
        try:
            start_time_str, end_time_str = self.operating_hours.split('-')
            start_time = datetime.strptime(start_time_str.strip(), '%H:%M').time()
            end_time = datetime.strptime(end_time_str.strip(), '%H:%M').time()
            
            return start_time <= current_time <= end_time
        except ValueError:
            return False
