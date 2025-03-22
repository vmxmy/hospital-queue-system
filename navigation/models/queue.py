from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db.models import Avg, Count, F, ExpressionWrapper, fields
from datetime import timedelta
import re
import hashlib
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver


class Queue(models.Model):
    """排队队列模型"""

    STATUS_CHOICES = [
        ('waiting', '等待中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('cancelled', '已取消'),
        ('skipped', '已过号'),
    ]

    patient = models.ForeignKey(
        'navigation.Patient',
        on_delete=models.CASCADE,
        verbose_name='患者'
    )
    department = models.ForeignKey(
        'navigation.Department',
        on_delete=models.CASCADE,
        verbose_name='科室'
    )
    equipment = models.ForeignKey(
        'navigation.Equipment',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='设备'
    )
    examination = models.ForeignKey(
        'navigation.Examination',
        on_delete=models.CASCADE,
        verbose_name='检查项目'
    )
    queue_number = models.CharField(
        '队列号',
        max_length=40,
        unique=True,
        editable=False
    )
    status = models.CharField(
        '状态',
        max_length=20,
        choices=STATUS_CHOICES,
        default='waiting'
    )
    priority = models.IntegerField(
        '优先级',
        default=0,
        help_text='队列优先级，继承自患者优先级，可单独调整'
    )
    estimated_wait_time = models.IntegerField(
        '预计等待时间(分钟)',
        validators=[MinValueValidator(0)],
        help_text='系统预测的等待时间'
    )
    actual_wait_time = models.IntegerField(
        '实际等待时间(分钟)',
        null=True,
        blank=True
    )
    enter_time = models.DateTimeField('进入队列时间', auto_now_add=True)
    start_time = models.DateTimeField('开始服务时间', null=True, blank=True)
    end_time = models.DateTimeField('结束服务时间', null=True, blank=True)
    notes = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '排队队列'
        verbose_name_plural = '排队队列'
        ordering = ['-priority', 'enter_time']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['queue_number']),
            models.Index(fields=['-priority', 'enter_time']),
        ]

    def __str__(self):
        return f"{self.department.name}-{self.queue_number}"

    def clean(self):
        """验证队列数据"""
        super().clean()
        
        # 验证设备是否属于正确的科室
        if self.equipment and self.equipment.department != self.department:
            raise ValidationError({
                'equipment': '设备不属于选择的科室'
            })
        
        # 验证检查项目是否属于正确的科室
        if self.examination.department != self.department:
            raise ValidationError({
                'examination': '检查项目不属于选择的科室'
            })
        
        # 验证是否超出科室每日最大接诊量
        if self.department.max_daily_patients:
            today = timezone.now().date()
            daily_count = Queue.objects.filter(
                department=self.department,
                created_at__date=today
            ).count()
            if daily_count >= self.department.max_daily_patients:
                raise ValidationError('该科室今日预约已满')
        
        # 验证患者是否有未完成的队列
        active_queue = Queue.objects.filter(
            patient=self.patient,
            status__in=['waiting', 'processing']
        ).exclude(pk=self.pk).first()
        if active_queue:
            raise ValidationError({
                'patient': f'患者在{active_queue.department.name}还有未完成的检查'
            })

    def save(self, *args, **kwargs):
        """保存队列记录"""
        # 如果是新创建的记录
        if not self.pk:
            # 设置初始优先级
            if not self.priority:
                self.priority = self.patient.priority
            
            # 生成队列号
            if not self.queue_number:
                self.queue_number = self.generate_queue_number()
            
            # 预估等待时间
            if not self.estimated_wait_time:
                self.estimated_wait_time = self.estimate_initial_wait_time()
        
        super().save(*args, **kwargs)

    def generate_queue_number(self):
        """生成队列号"""
        now = timezone.now()
        
        # 新格式的队列号：{科室代码}{生成日期:YYYYMMDD}{队列号生成时间:HHMMSS}{患者姓名哈希加密后的后4位}
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
        
        queue_number = f"{self.department.code}{date_str}{time_str}{hash_suffix}"
        
        # 验证队列号唯一性
        while Queue.objects.filter(queue_number=queue_number).exists():
            # 如果存在重复，附加随机字符
            import random
            suffix = ''.join(random.choices('0123456789abcdef', k=4))
            queue_number = f"{self.department.code}{date_str}{time_str}{suffix}"
        
        return queue_number

    def estimate_initial_wait_time(self):
        """预估初始等待时间"""
        try:
            from navigation.ml.prophet_predictor import get_prophet_predictor
            
            # 获取当前等待和处理中的队列数量（考虑优先级）
            waiting_queues = Queue.objects.filter(
                department=self.department,
                status='waiting',
                priority__gte=self.priority  # 高优先级排在前面
            )
            
            # 获取前面等待的人数
            position = 0
            if self.id:  # 已有ID的情况（更新）
                position = Queue.objects.filter(
                    department=self.department,
                    status='waiting',
                    priority__gt=self.priority,  # 更高优先级的
                ).count() + Queue.objects.filter(
                    department=self.department,
                    status='waiting',
                    priority=self.priority,  # 相同优先级的
                    enter_time__lt=self.enter_time  # 但先到的
                ).count()
            else:  # 新创建
                position = waiting_queues.count()
            
            # 1. 获取该检查项目的历史实际等待时间（过去30天）
            thirty_days_ago = timezone.now() - timedelta(days=30)
            historical_data = Queue.objects.filter(
                examination=self.examination,
                status='completed',
                start_time__isnull=False,  # 确保有开始时间
                enter_time__gte=thirty_days_ago,
                actual_wait_time__isnull=False  # 确保有实际等待时间
            )
            
            # 2. 获取历史平均等待时间
            avg_historical_wait_time = 0
            if historical_data.exists():
                avg_historical_wait_time = historical_data.aggregate(avg_wait=Avg('actual_wait_time'))['avg_wait'] or 0
            
            # 3. 获取历史人均服务时间（从开始服务到结束的时间）
            historical_service_times = Queue.objects.filter(
                examination=self.examination,
                status='completed',
                start_time__isnull=False,
                end_time__isnull=False,
                enter_time__gte=thirty_days_ago
            )
            
            avg_service_time = 0
            if historical_service_times.exists():
                # 计算服务时间（分钟）
                service_times = [
                    (q.end_time - q.start_time).total_seconds() / 60 
                    for q in historical_service_times
                ]
                avg_service_time = sum(service_times) / len(service_times)
            
            # 如果没有历史服务时间，使用设备/检查的时间
            if avg_service_time <= 0:
                if self.equipment:
                    avg_service_time = self.equipment.average_service_time
                else:
                    avg_service_time = self.examination.duration
            
            # 4. 计算当前排队人数产生的基础等待时间
            base_wait_time = position * avg_service_time
            
            # 5. 尝试使用Prophet预测
            prophet_wait_time = None
            prophet_weight = 0.4  # Prophet模型权重
            
            # 优先使用检查项目级别的Prophet模型
            try:
                # 获取检查项目的Prophet预测器
                predictor = get_prophet_predictor(examination_id=self.examination.id)
                if predictor and predictor.model:
                    # 使用Prophet预测，传入当前队列数量作为额外信息
                    prophet_wait_time = predictor.predict(
                        date=timezone.now(), 
                        queue_count=position
                    )
            except Exception as e:
                logger.warning(f"使用检查项目Prophet模型预测失败: {str(e)}")
            
            # 如果检查项目级别失败，尝试科室级别
            if prophet_wait_time is None:
                try:
                    # 获取科室的Prophet预测器
                    predictor = get_prophet_predictor(department_id=self.department.id)
                    if predictor and predictor.model:
                        # 使用Prophet预测，传入当前队列数量作为额外信息
                        prophet_wait_time = predictor.predict(
                            date=timezone.now(), 
                            queue_count=position
                        )
                except Exception as e:
                    logger.warning(f"使用科室Prophet模型预测失败: {str(e)}")
            
            # 如果科室级别也失败，尝试全局模型
            if prophet_wait_time is None:
                try:
                    # 获取全局Prophet预测器
                    predictor = get_prophet_predictor()
                    if predictor and predictor.model:
                        # 使用Prophet预测，传入当前队列数量作为额外信息
                        prophet_wait_time = predictor.predict(
                            date=timezone.now(), 
                            queue_count=position
                        )
                except Exception as e:
                    logger.warning(f"使用全局Prophet模型预测失败: {str(e)}")
            
            # 6. 如果有Prophet预测结果，与传统方法结合
            if prophet_wait_time is not None:
                # 综合考虑历史数据、基础等待时间和Prophet预测
                # 使用加权平均: 历史数据(0.2) + 基础计算(0.4) + Prophet预测(0.4)
                if avg_historical_wait_time > 0:
                    adjusted_wait_time = (avg_historical_wait_time * 0.2) + (base_wait_time * 0.4) + (prophet_wait_time * prophet_weight)
                else:
                    adjusted_wait_time = (base_wait_time * 0.6) + (prophet_wait_time * prophet_weight)
            else:
                # 如果没有Prophet预测，使用原始算法
                if avg_historical_wait_time > 0:
                    # 综合考虑历史等待时间和基础等待时间
                    # 使用加权平均，历史数据权重0.3，当前计算权重0.7
                    adjusted_wait_time = (avg_historical_wait_time * 0.3) + (base_wait_time * 0.7)
                else:
                    adjusted_wait_time = base_wait_time
            
            # 7. 根据优先级调整等待时间
            priority_factor = max(1 - (self.priority * 0.2), 0.2)  # 每级优先级减少20%等待时间
            final_wait_time = adjusted_wait_time * priority_factor
            
            # 8. 获取正在处理中的队列信息，调整等待时间
            processing_queues = Queue.objects.filter(
                department=self.department,
                status='processing'
            )
            
            # 如果有处理中的队列，且数量少于科室设备数，减少等待时间
            equipment_count = self.department.equipment_set.filter(status='available').count()
            if equipment_count > 0 and processing_queues.count() < equipment_count:
                free_capacity_factor = 1 - ((equipment_count - processing_queues.count()) / equipment_count * 0.5)
                final_wait_time *= max(free_capacity_factor, 0.5)  # 最多减少50%
            
            # 9. 最小等待时间保护
            final_wait_time = max(avg_service_time * 0.5, final_wait_time)  # 至少等待半个服务时间
            
            return round(final_wait_time)
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"预估等待时间出错: {str(e)}")
            
            # 使用传统方法的简化版本作为后备
            try:
                position = self.get_position() or 1
                avg_service_time = self.examination.duration
                if self.equipment:
                    avg_service_time = self.equipment.average_service_time
                
                return max(5, round(position * avg_service_time * 0.8))  # 给一个保守估计
            except:
                return 30  # 默认30分钟

    def calculate_wait_time(self):
        """计算实际等待时间"""
        if self.start_time:
            duration = self.start_time - self.enter_time
            return duration.total_seconds() / 60
        return None

    def update_status(self, new_status):
        """更新队列状态"""
        if new_status == self.status:
            return
        
        if new_status == 'processing':
            self.start_time = timezone.now()
        elif new_status in ['completed', 'cancelled', 'skipped']:
            self.end_time = timezone.now()
            if self.start_time:
                self.actual_wait_time = self.calculate_wait_time()
        
        # 保存旧状态
        old_status = self.status
        
        # 更新状态并保存
        self.status = new_status
        self.save()
        
        # 对于已完成、已取消或已过号的队列，创建历史记录
        if new_status in ['completed', 'cancelled', 'skipped']:
            try:
                from .queue_history import QueueHistory
                QueueHistory.create_from_queue(self)
                logger = logging.getLogger(__name__)
                logger.info(f"为队列 {self.queue_number} 创建了历史记录，状态: {new_status}")
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"创建队列历史记录失败: {str(e)}")

    def get_position(self):
        """获取在队列中的位置"""
        if self.status != 'waiting':
            return None
            
        return Queue.objects.filter(
            department=self.department,
            status='waiting',
            priority__gte=self.priority,
            enter_time__lte=self.enter_time
        ).count()

    @property
    def is_delayed(self):
        """检查是否超时"""
        if self.status != 'waiting':
            return False
        
        elapsed_time = (timezone.now() - self.enter_time).total_seconds() / 60
        return elapsed_time > self.estimated_wait_time

    def recalculate_wait_time(self):
        """重新计算预计等待时间"""
        new_estimate = self.estimate_initial_wait_time()
        if new_estimate != self.estimated_wait_time:
            self.estimated_wait_time = new_estimate
            self.save(update_fields=['estimated_wait_time'])
            
    @staticmethod
    def recalculate_all_wait_times():
        """重新计算所有等待中的队列的等待时间"""
        # 获取所有等待中的队列
        waiting_queues = Queue.objects.filter(status='waiting')
        
        updated_count = 0
        for queue in waiting_queues:
            old_wait_time = queue.estimated_wait_time
            new_wait_time = queue.estimate_initial_wait_time()
            
            if old_wait_time != new_wait_time:
                queue.estimated_wait_time = new_wait_time
                queue.save(update_fields=['estimated_wait_time'])
                updated_count += 1
        
        return updated_count

@receiver(post_save, sender=Queue)
def queue_post_save(sender, instance, created, **kwargs):
    """在Queue保存后更新关联的QueueRecord"""
    if not created and hasattr(instance, 'queuerecord'):
        record = instance.queuerecord
        record.call_time = instance.start_time
        record.finish_time = instance.end_time
        record.status = instance.status
        record.save()
