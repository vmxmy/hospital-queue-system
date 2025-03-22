from django.db import models
from django.core.validators import MinValueValidator


class Equipment(models.Model):
    """设备模型"""

    STATUS_CHOICES = [
        ('available', '可用'),
        ('in_use', '使用中'),
        ('maintenance', '维护中'),
        ('offline', '离线'),
    ]

    name = models.CharField('设备名称', max_length=100)
    code = models.CharField('设备编号', max_length=50, unique=True)
    model = models.CharField('型号', max_length=100)
    manufacturer = models.CharField('制造商', max_length=100)
    department = models.ForeignKey(
        'navigation.Department',
        on_delete=models.CASCADE,
        verbose_name='所属科室'
    )
    location = models.CharField('具体位置', max_length=200)
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='available'
    )
    description = models.TextField('设备描述', blank=True)
    maintenance_period = models.IntegerField(
        '维护周期(天)',
        validators=[MinValueValidator(1)],
        help_text='设备需要定期维护的间隔天数'
    )
    last_maintenance_date = models.DateField(
        '上次维护日期',
        null=True,
        blank=True
    )
    next_maintenance_date = models.DateField(
        '下次维护日期',
        null=True,
        blank=True
    )
    average_service_time = models.IntegerField(
        '平均检查时间(分钟)',
        validators=[MinValueValidator(1)],
        help_text='平均每位患者的检查时间'
    )
    notes = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备'
        ordering = ['department', 'name']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.name}({self.code})"

    def is_available(self):
        """检查设备是否可用"""
        return self.status == 'available'

    def needs_maintenance(self):
        """检查设备是否需要维护"""
        from django.utils import timezone
        if not self.next_maintenance_date:
            return False
        return self.next_maintenance_date <= timezone.now().date()

    def update_status(self, new_status):
        """更新设备状态"""
        if new_status == self.status:
            return
        
        self.status = new_status
        self.save()

    def schedule_maintenance(self, maintenance_date):
        """安排设备维护"""
        from django.utils import timezone
        from datetime import timedelta
        
        self.last_maintenance_date = maintenance_date
        self.next_maintenance_date = maintenance_date + timedelta(
            days=self.maintenance_period
        )
        self.status = 'maintenance'
        self.save()
