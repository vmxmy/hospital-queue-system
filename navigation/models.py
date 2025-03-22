from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
import json
import hashlib

# Create your models here.

# 医院科室模型
class Department(models.Model):
    name = models.CharField('科室名称', max_length=100)
    code = models.CharField('科室代码', max_length=20, unique=True)
    description = models.TextField('科室描述', blank=True, null=True)
    location = models.CharField('位置', max_length=200, blank=True, null=True)
    floor = models.IntegerField('楼层', blank=True, null=True)
    building = models.CharField('楼栋', max_length=100, blank=True, null=True)
    contact_phone = models.CharField('联系电话', max_length=20, blank=True, null=True)
    operating_hours = models.CharField('运营时间', max_length=100, blank=True, null=True)
    max_daily_patients = models.IntegerField('每日最大患者数', default=100)
    average_service_time = models.IntegerField('平均服务时间(分钟)', default=15)
    is_active = models.BooleanField('是否启用', default=True)
    notes = models.TextField('备注', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '科室'
        verbose_name_plural = '科室'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_current_queue_count(self):
        """获取当前等待队列数量"""
        return self.queue_set.filter(status='waiting').count()

    def get_average_wait_time(self):
        """获取科室平均等待时间"""
        today = timezone.now().date()
        completed_queues = self.queue_set.filter(
            status='completed',
            end_time__date=today
        )
        if not completed_queues.exists():
            return self.average_service_time
        
        total_time = sum((q.end_time - q.enter_time).total_seconds() / 60 for q in completed_queues if q.end_time)
        return int(total_time / completed_queues.count())

# 检查设备模型
class Equipment(models.Model):
    name = models.CharField('设备名称', max_length=100)
    code = models.CharField('设备代码', max_length=20, unique=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='所属科室')
    model = models.CharField('型号', max_length=100, blank=True, null=True)
    manufacturer = models.CharField('制造商', max_length=100, blank=True, null=True)
    location = models.CharField('位置', max_length=200, blank=True, null=True)
    status = models.CharField('状态', max_length=20, choices=[
        ('available', '可用'),
        ('in_use', '使用中'),
        ('maintenance', '维护中'),
        ('out_of_service', '停用')
    ], default='available')
    average_service_time = models.IntegerField('平均检查时间(分钟)', default=15)
    is_active = models.BooleanField('是否启用', default=True)
    notes = models.TextField('备注', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '设备'
        verbose_name_plural = '设备'

    def __str__(self):
        return f"{self.name} ({self.department.name})"

# 检查项目模型
class Examination(models.Model):
    name = models.CharField('检查名称', max_length=100)
    code = models.CharField('检查代码', max_length=20, unique=True)
    description = models.TextField('检查描述', blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, verbose_name='所属科室')
    equipment = models.ManyToManyField(Equipment, blank=True, verbose_name='可用设备')
    duration = models.IntegerField('检查时长(分钟)', default=15)
    price = models.DecimalField('价格', max_digits=10, decimal_places=2, default=0.0)
    preparation = models.TextField('准备工作', blank=True, null=True)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '检查项目'
        verbose_name_plural = '检查项目'

    def __str__(self):
        return f"{self.name} ({self.department.name})"

# 患者模型
class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='用户账号', null=True, blank=True)
    name = models.CharField('姓名', max_length=100)
    gender = models.CharField('性别', max_length=10, choices=[
        ('male', '男'),
        ('female', '女'),
        ('other', '其他')
    ])
    birth_date = models.DateField('出生日期', null=True, blank=True)
    id_number = models.CharField('身份证号', max_length=18, unique=True, null=True, blank=True)
    phone = models.CharField('电话', max_length=20)
    address = models.CharField('地址', max_length=200, blank=True, null=True)
    medical_record_number = models.CharField('病历号', max_length=50, unique=True)
    priority = models.IntegerField('优先级', choices=[
        (0, '普通'),
        (1, '加急'),
        (2, '特急'),
        (3, '危急'),
    ], default=0)
    special_needs = models.TextField('特殊需求', blank=True, null=True)
    medical_history = models.TextField('病史', blank=True, null=True)
    allergies = models.TextField('过敏史', blank=True, null=True)
    notes = models.TextField('备注', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '患者'
        verbose_name_plural = '患者'

    def __str__(self):
        return f"{self.name} ({self.medical_record_number})"

    def age(self):
        if not self.birth_date:
            return None
        today = timezone.now().date()
        return today.year - self.birth_date.year - (
            (today.month, today.day) < (self.birth_date.month, self.birth_date.day)
        )
    
    def get_active_queues(self):
        """获取患者活跃中的队列"""
        return self.queue_set.filter(status__in=['waiting', 'processing'])
    
    def get_queues_history(self):
        """获取患者的排队历史"""
        return self.queue_set.filter(status__in=['completed', 'cancelled'])

# 排队模型
class Queue(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='queues')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='queues')
    equipment = models.ForeignKey(Equipment, on_delete=models.SET_NULL, related_name='queues', null=True, blank=True)
    examination = models.ForeignKey(Examination, on_delete=models.CASCADE, related_name='queues')
    queue_number = models.CharField(max_length=40, unique=True)
    STATUS_CHOICES = (
        ('waiting', '等待中'),
        ('processing', '处理中'),
        ('in_service', '服务中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('skipped', '已过号'),
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    PRIORITY_CHOICES = (
        (0, '正常'),
        (1, '加急'),
        (2, '紧急'),
        (3, '危急'),
    )
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=0)
    estimated_wait_time = models.IntegerField(help_text='Estimated wait time in minutes', default=0)
    actual_wait_time = models.IntegerField(help_text='Actual wait time in minutes', null=True, blank=True)
    enter_time = models.DateTimeField(auto_now_add=True)
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # 生成队列号
        if not self.queue_number:
            # 新格式的队列号：{科室代码}{生成日期:YYYYMMDD}{队列号生成时间:HHMMSS}{患者姓名哈希加密后的后4位}
            import datetime
            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            
            # 计算患者姓名的哈希值后4位
            if hasattr(self, 'patient') and self.patient and self.patient.name:
                # 使用MD5哈希算法计算患者姓名的哈希值
                name_hash = hashlib.md5(self.patient.name.encode('utf-8')).hexdigest()
                # 获取哈希值的后4位
                hash_suffix = name_hash[-4:]
            else:
                # 如果没有患者信息，使用随机的4位字符
                import random
                hash_suffix = ''.join(random.choices('0123456789abcdef', k=4))
            
            self.queue_number = f"{self.department.code}{date_str}{time_str}{hash_suffix}"
            
            # 验证队列号唯一性
            while Queue.objects.filter(queue_number=self.queue_number).exists():
                # 如果存在重复，附加随机字符
                import random
                suffix = ''.join(random.choices('0123456789abcdef', k=4))
                self.queue_number = f"{self.department.code}{date_str}{time_str}{suffix}"
        
        # 当状态变更为"服务中"或"处理中"时，记录开始时间
        if self.status in ['in_service', 'processing'] and not self.start_time:
            self.start_time = timezone.now()
        
        # 当状态变更为"已完成"时，记录结束时间和计算实际等待时间
        if self.status == 'completed' and not self.end_time:
            self.end_time = timezone.now()
            if self.start_time:
                # 计算从进入队列到开始服务的等待时间（分钟）
                wait_duration = self.start_time - self.enter_time
                self.actual_wait_time = int(wait_duration.total_seconds() // 60)
        
        super(Queue, self).save(*args, **kwargs)

    class Meta:
        ordering = ['-priority', 'enter_time']
        
    def __str__(self):
        return f"{self.queue_number} - {self.status}"

    def get_position(self):
        """
        获取当前病人在队列中的位置
        """
        if self.status != 'waiting':
            return 0
            
        ahead_patients = Queue.objects.filter(
            department=self.department,
            status='waiting',
            priority__gte=self.priority,
            enter_time__lt=self.enter_time
        ).count()
        
        # 返回的位置包括自己，所以+1
        return ahead_patients + 1
    
    def estimate_initial_wait_time(self):
        """预估初始等待时间"""
        # 获取当前等待和处理中的队列数量
        waiting_count = Queue.objects.filter(
            department=self.department,
            status__in=['waiting', 'processing', 'in_service'],
            priority__gte=self.priority  # 考虑优先级
        ).count()
        
        # 如果指定了设备，使用设备的平均服务时间
        if self.equipment:
            avg_service_time = self.equipment.average_service_time
        # 否则使用检查项目的标准时长
        else:
            avg_service_time = self.examination.duration
        
        # 基础等待时间 = 前面等待人数 × 平均服务时间
        base_wait_time = waiting_count * avg_service_time
        
        # 根据优先级调整等待时间
        priority_factor = max(1 - (self.priority * 0.2), 0.2)  # 每级优先级减少20%等待时间
        adjusted_wait_time = base_wait_time * priority_factor
        
        return round(adjusted_wait_time)
    
    def recalculate_wait_time(self):
        """重新计算预计等待时间"""
        new_estimate = self.estimate_initial_wait_time()
        if new_estimate != self.estimated_wait_time:
            self.estimated_wait_time = new_estimate
            self.save(update_fields=['estimated_wait_time'])

# 通知模板分类
class NotificationCategory(models.Model):
    name = models.CharField('分类名称', max_length=100)
    code = models.CharField('分类代码', max_length=20, unique=True)
    description = models.TextField('分类描述', blank=True, null=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '通知分类'
        verbose_name_plural = '通知分类'

    def __str__(self):
        return self.name

# 通知模板
class NotificationTemplate(models.Model):
    category = models.ForeignKey(NotificationCategory, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='分类')
    code = models.CharField('模板代码', max_length=50, unique=True)
    title = models.CharField('标题', max_length=200)
    content = models.TextField('内容')
    channel_types = models.JSONField('渠道类型', default=list)
    sms_template_code = models.CharField('短信模板代码', max_length=100, blank=True, null=True)
    wechat_template_id = models.CharField('微信模板ID', max_length=100, blank=True, null=True)
    description = models.TextField('描述', blank=True, null=True)
    variables = models.JSONField('变量列表', default=list)
    priority = models.IntegerField('优先级', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '通知模板'
        verbose_name_plural = '通知模板'

    def __str__(self):
        return f"{self.code} - {self.title}"
    
    def render(self, context):
        """
        渲染模板内容
        """
        content = self.content
        for key, value in context.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))
        return content

# 通知统计
class NotificationStats(models.Model):
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, verbose_name='通知模板')
    channel = models.CharField('通知渠道', max_length=20)
    sent_count = models.IntegerField('发送数量', default=0)
    success_count = models.IntegerField('成功数量', default=0)
    fail_count = models.IntegerField('失败数量', default=0)
    date = models.DateField('统计日期', default=timezone.now)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '通知统计'
        verbose_name_plural = '通知统计'
        unique_together = ['template', 'channel', 'date']

    def __str__(self):
        return f"{self.template.code} - {self.channel} - {self.date}"
