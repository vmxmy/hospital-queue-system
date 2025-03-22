from django.db import models
from .notification_template import NotificationTemplate

class NotificationStats(models.Model):
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, verbose_name='通知模板')
    channel = models.CharField(max_length=20, verbose_name='通知渠道')
    sent_count = models.IntegerField(default=0, verbose_name='发送次数')
    success_count = models.IntegerField(default=0, verbose_name='成功次数')
    fail_count = models.IntegerField(default=0, verbose_name='失败次数')
    date = models.DateField(verbose_name='统计日期')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '通知统计'
        verbose_name_plural = verbose_name
        unique_together = ('template', 'channel', 'date')
        indexes = [
            models.Index(fields=['template', 'date']),
            models.Index(fields=['channel', 'date']),
        ]

    def __str__(self):
        return f"{self.template.code} - {self.channel} - {self.date}"

    @classmethod
    def record_sent(cls, template, channel, success=True):
        """
        记录通知发送结果
        """
        from django.utils import timezone
        today = timezone.now().date()
        
        stats, _ = cls.objects.get_or_create(
            template=template,
            channel=channel,
            date=today,
            defaults={
                'sent_count': 0,
                'success_count': 0,
                'fail_count': 0
            }
        )
        
        stats.sent_count += 1
        if success:
            stats.success_count += 1
        else:
            stats.fail_count += 1
        
        stats.save() 