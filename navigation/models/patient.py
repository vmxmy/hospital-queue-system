from django.db import models
from django.contrib.auth.models import User


class Patient(models.Model):
    """患者模型"""

    GENDER_CHOICES = [
        ('M', '男'),
        ('F', '女'),
        ('O', '其他'),
    ]

    PRIORITY_CHOICES = [
        (0, '普通'),
        (1, '加急'),
        (2, '特急'),
        (3, '危急'),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='用户账号',
        null=True,
        blank=True
    )
    name = models.CharField('姓名', max_length=50)
    id_number = models.CharField('身份证号', max_length=18, unique=True)
    gender = models.CharField('性别', max_length=1, choices=GENDER_CHOICES)
    birth_date = models.DateField('出生日期')
    phone = models.CharField('联系电话', max_length=20)
    address = models.CharField('地址', max_length=200, blank=True)
    medical_record_number = models.CharField('病历号', max_length=50, unique=True)
    priority = models.IntegerField(
        '优先级',
        choices=PRIORITY_CHOICES,
        default=0,
        help_text='患者优先级，影响排队顺序'
    )
    special_needs = models.TextField('特殊需求', blank=True)
    medical_history = models.TextField('病史', blank=True)
    allergies = models.TextField('过敏史', blank=True)
    notes = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '患者'
        verbose_name_plural = '患者'
        ordering = ['-priority', 'created_at']
        indexes = [
            models.Index(fields=['id_number']),
            models.Index(fields=['medical_record_number']),
        ]

    def __str__(self):
        return f"{self.name}({self.medical_record_number})"

    def get_age(self):
        """计算患者年龄"""
        from django.utils import timezone
        today = timezone.now().date()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )

    def get_current_queue(self):
        """获取患者当前排队信息"""
        return self.queue_set.filter(
            status__in=['waiting', 'processing']
        ).first()

    def get_queue_history(self):
        """获取患者历史排队记录"""
        return self.queue_set.filter(
            status__in=['completed', 'cancelled', 'skipped']
        ).order_by('-created_at')

    def get_current_queues(self):
        """获取患者当前所有排队信息"""
        return self.queue_set.filter(status='waiting')

    def get_completed_examinations(self):
        """获取已完成的检查"""
        return self.examination_set.filter(status='completed')

    def get_pending_examinations(self):
        """获取待完成的检查"""
        return self.examination_set.exclude(status='completed')
