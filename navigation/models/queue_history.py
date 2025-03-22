from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class QueueHistory(models.Model):
    """队列历史记录模型，用于记录队列状态变更历史"""
    
    queue = models.ForeignKey('Queue', on_delete=models.CASCADE, verbose_name='关联队列')
    queue_number = models.CharField(max_length=20, db_index=True, verbose_name='队列号')
    status = models.CharField(max_length=20, db_index=True, verbose_name='状态')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    
    estimated_wait_time = models.IntegerField(default=0, verbose_name='预计等待时间(分钟)')
    actual_wait_time = models.IntegerField(default=0, verbose_name='实际等待时间(分钟)')
    
    enter_time = models.DateTimeField(verbose_name='进入时间')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    exit_time = models.DateTimeField(null=True, blank=True, verbose_name='退出时间')
    
    notes = models.TextField(blank=True, verbose_name='备注')
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    # 关联字段
    department = models.ForeignKey('Department', on_delete=models.CASCADE, verbose_name='科室')
    equipment = models.ForeignKey('Equipment', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='设备')
    examination = models.ForeignKey('Examination', on_delete=models.CASCADE, verbose_name='检查项目')
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, verbose_name='患者')
    
    class Meta:
        verbose_name = '队列历史'
        verbose_name_plural = '队列历史'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['queue_number']),
            models.Index(fields=['enter_time']),
            models.Index(fields=['exit_time']),
        ]
        
    def __str__(self):
        return f"{self.queue_number} - {self.patient} ({self.status})"
    
    @classmethod
    def create_from_queue(cls, queue):
        """
        从队列对象创建历史记录
        
        参数:
        - queue: Queue对象
        
        返回:
        - 创建的QueueHistory对象
        """
        if queue.status not in ['completed', 'cancelled', 'skipped']:
            raise ValueError(f"只能为已完成、已取消或已过号的队列创建历史记录，当前状态: {queue.status}")
        
        history = cls(
            queue=queue,
            patient=queue.patient,
            department=queue.department,
            equipment=queue.equipment,
            examination=queue.examination,
            queue_number=queue.queue_number,
            status=queue.status,
            priority=queue.priority,
            estimated_wait_time=queue.estimated_wait_time,
            actual_wait_time=queue.actual_wait_time,
            enter_time=queue.enter_time,
            start_time=queue.start_time,
            exit_time=queue.end_time or timezone.now(),
            notes=queue.notes
        )
        history.save()
        return history 