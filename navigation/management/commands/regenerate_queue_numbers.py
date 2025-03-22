import datetime
import random
import hashlib
from django.core.management.base import BaseCommand
from django.utils import timezone
from navigation.models import Queue, Department

class Command(BaseCommand):
    help = '将现有队列记录的队列号重新格式化为新格式: {科室代码}{生成日期:YYYYMMDD}{队列号生成时间:HHMMSS}{患者姓名哈希加密后的后4位}'

    def handle(self, *args, **options):
        # 获取所有队列记录
        queues = Queue.objects.all().order_by('created_at')
        total_count = queues.count()
        self.stdout.write(self.style.SUCCESS(f'开始处理 {total_count} 条队列记录...'))
        
        # 获取所有科室
        departments = {dept.id: dept for dept in Department.objects.all()}
        
        updated_count = 0
        used_queue_numbers = set()  # 记录已使用的队列号以避免重复
        
        # 按时间顺序处理每个队列记录
        base_time = timezone.now()
        
        for i, queue in enumerate(queues):
            # 获取科室代码
            dept = departments.get(queue.department_id)
            if not dept:
                self.stdout.write(self.style.WARNING(f'找不到科室ID: {queue.department_id}，跳过记录 {queue.id}'))
                continue
            
            # 保存旧队列号以便输出
            old_queue_number = queue.queue_number
            
            # 生成一个基于索引的时间偏移，确保每个队列号都与时间相关且唯一
            # 使用队列的创建时间为基础，加上序号确保唯一性
            created_time = queue.created_at
            date_str = created_time.strftime("%Y%m%d")
            
            # 为每条记录添加一个唯一的毫秒值（使用记录索引）
            time_ms = (created_time.hour * 3600 + created_time.minute * 60 + created_time.second) * 1000 + i % 1000
            # 格式化为时分秒毫秒
            hours = time_ms // 3600000
            mins = (time_ms % 3600000) // 60000
            secs = (time_ms % 60000) // 1000
            ms = i % 1000  # 使用索引的后三位作为毫秒，确保唯一性
            
            time_str = f"{hours:02d}{mins:02d}{secs:02d}{ms:03d}"
            
            # 计算患者姓名的哈希值后4位
            if hasattr(queue, 'patient') and queue.patient and queue.patient.name:
                # 使用MD5哈希算法计算患者姓名的哈希值
                name_hash = hashlib.md5(queue.patient.name.encode('utf-8')).hexdigest()
                # 获取哈希值的后4位
                hash_suffix = name_hash[-4:]
            else:
                # 如果没有患者信息，使用随机的4位字符
                hash_suffix = hashlib.md5(str(queue.id).encode('utf-8')).hexdigest()[-4:]
            
            # 生成新格式的队列号
            new_queue_number = f"{dept.code}{date_str}{time_str}{hash_suffix}"
            
            # 确保队列号唯一
            attempt = 0
            original_number = new_queue_number
            while new_queue_number in used_queue_numbers:
                attempt += 1
                new_queue_number = f"{original_number}{attempt}"
            
            used_queue_numbers.add(new_queue_number)
            
            # 直接使用SQL更新队列号，避免触发模型的save方法
            Queue.objects.filter(id=queue.id).update(queue_number=new_queue_number)
            
            updated_count += 1
            
            # 每100条记录输出一次进度
            if updated_count % 100 == 0 or updated_count == 1:
                self.stdout.write(f'已处理 {updated_count}/{total_count} 条记录...')
                self.stdout.write(f'示例: {old_queue_number} -> {new_queue_number}')
        
        self.stdout.write(self.style.SUCCESS(f'完成! 共更新了 {updated_count} 条队列记录的队列号。')) 