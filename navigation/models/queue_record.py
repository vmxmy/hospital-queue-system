from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

class QueueRecord(models.Model):
    """队列记录模型，用于记录患者的完整就诊过程"""
    
    patient = models.ForeignKey('Patient', on_delete=models.CASCADE, verbose_name='患者')
    examination_item = models.ForeignKey('Examination', on_delete=models.CASCADE, verbose_name='检查项目')
    queue = models.OneToOneField('Queue', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='关联队列')
    
    check_in_time = models.DateTimeField(verbose_name='签到时间')
    call_time = models.DateTimeField(null=True, blank=True, verbose_name='叫号时间')
    finish_time = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    queue_time = models.IntegerField(default=0, verbose_name='排队时间(分钟)')
    service_time = models.IntegerField(default=0, verbose_name='服务时间(分钟)')
    
    STATUS_CHOICES = [
        ('waiting', '等待中'),
        ('in_service', '服务中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('no_show', '未到'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='状态')
    
    created_at = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '队列记录'
        verbose_name_plural = '队列记录'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['check_in_time']),
            models.Index(fields=['call_time']),
            models.Index(fields=['finish_time']),
        ]
        
    def __str__(self):
        return f"{self.patient} - {self.examination_item} ({self.get_status_display()})"
    
    def update_times(self):
        """更新排队时间和服务时间"""
        now = timezone.now()
        
        # 计算排队时间（从签到到叫号的时间）
        if self.call_time and self.check_in_time:
            self.queue_time = int((self.call_time - self.check_in_time).total_seconds() / 60)
            
        # 计算服务时间（从叫号到完成的时间）
        if self.finish_time and self.call_time:
            self.service_time = int((self.finish_time - self.call_time).total_seconds() / 60)

@receiver(pre_save, sender=QueueRecord)
def queue_record_pre_save(sender, instance, **kwargs):
    """在保存前更新时间"""
    instance.update_times()

@receiver(post_save, sender=QueueRecord)
def queue_record_post_save(sender, instance, created, **kwargs):
    """在保存后更新关联的Queue状态"""
    from .queue import Queue
    from .queue_history import QueueHistory
    
    if instance.queue:
        # 更新Queue的状态
        instance.queue.status = instance.status
        instance.queue.save()
        
        # 创建QueueHistory记录
        QueueHistory.objects.create(
            queue=instance.queue,
            queue_number=instance.queue.queue_number,
            status=instance.status,
            patient=instance.patient,
            examination=instance.examination_item,
            department=instance.examination_item.department,
            equipment=instance.examination_item.equipment,
            enter_time=instance.check_in_time,
            start_time=instance.call_time,
            exit_time=instance.finish_time,
            estimated_wait_time=instance.queue.estimated_wait_time,
            actual_wait_time=instance.queue_time,
            priority=instance.queue.priority
        ) 