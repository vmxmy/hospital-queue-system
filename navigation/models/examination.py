from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Examination(models.Model):
    """检查项目模型"""

    name = models.CharField('项目名称', max_length=100)
    code = models.CharField('项目代码', max_length=50, unique=True)
    department = models.ForeignKey(
        'navigation.Department',
        on_delete=models.CASCADE,
        verbose_name='所属科室'
    )
    equipment_type = models.ManyToManyField(
        'navigation.Equipment',
        verbose_name='可用设备',
        help_text='可以进行此项检查的设备列表'
    )
    description = models.TextField('项目描述')
    preparation = models.TextField(
        '检查准备事项',
        help_text='患者需要进行的准备工作'
    )
    contraindications = models.TextField(
        '禁忌症',
        blank=True,
        help_text='不适合进行此项检查的情况'
    )
    duration = models.IntegerField(
        '标准检查时长(分钟)',
        validators=[MinValueValidator(1)],
        help_text='标准情况下完成检查需要的时间'
    )
    price = models.DecimalField(
        '检查费用',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )
    is_active = models.BooleanField('是否启用', default=True)
    notes = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '检查项目'
        verbose_name_plural = '检查项目'
        ordering = ['department', 'name']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.name}({self.code})"

    def get_available_equipment(self):
        """获取当前可用的设备列表"""
        return self.equipment_type.filter(status='available')

    def estimate_wait_time(self, department=None):
        """估算当前检查项目的等待时间"""
        available_equipment = self.get_available_equipment()
        if not available_equipment:
            return float('inf')
        
        if department:
            available_equipment = available_equipment.filter(
                department=department
            )
            if not available_equipment:
                return float('inf')
        
        # 找到等待时间最短的设备
        min_wait_time = float('inf')
        for equipment in available_equipment:
            current_queues = equipment.queue_set.filter(
                status='waiting'
            ).count()
            wait_time = current_queues * equipment.average_service_time
            min_wait_time = min(min_wait_time, wait_time)
        
        return min_wait_time
