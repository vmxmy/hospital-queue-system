import os
import sys
import django
import random
import logging
from datetime import datetime, timedelta
from tqdm import tqdm

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

from navigation.models import Patient, Examination, QueueRecord
from django.db import transaction
from django.utils import timezone

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_random_time(base_date):
    """生成随机的检查时间"""
    # 生成8:00到17:00之间的随机时间
    hour = random.randint(8, 16)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return base_date.replace(hour=hour, minute=minute, second=second)

def generate_service_time(exam_duration):
    """根据检查项目的标准时长生成实际服务时间"""
    # 实际服务时间在标准时长的80%-120%之间浮动
    min_time = int(exam_duration * 0.8)
    max_time = int(exam_duration * 1.2)
    return random.randint(min_time, max_time)

def generate_queue_time():
    """生成合理的排队时间（分钟）"""
    # 大多数排队在0-40分钟之间，少数可能会更长
    weights = [4] * 10 + [3] * 15 + [2] * 10 + [1] * 5  # 权重分布
    return random.choices(range(0, 41), weights=weights)[0]

def generate_queue_records():
    """生成20000条队列记录"""
    try:
        # 获取所有患者和检查项目
        patients = list(Patient.objects.all())
        examination_items = list(Examination.objects.filter(is_active=True))
        
        if not patients or not examination_items:
            logger.error("没有找到患者或检查项目数据")
            return
            
        logger.info(f"开始生成20000条队列记录...")
        
        # 生成过去90天的记录
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=90)
        
        # 准备批量创建的记录
        records_to_create = []
        
        for _ in tqdm(range(20000), desc="生成队列记录"):
            # 随机选择日期
            random_date = start_date + timedelta(days=random.randint(0, 90))
            
            # 随机选择患者和检查项目
            patient = random.choice(patients)
            exam_item = random.choice(examination_items)
            
            # 生成检查时间
            check_time = generate_random_time(datetime.combine(random_date, datetime.min.time()))
            
            # 生成服务时间和排队时间
            service_time = generate_service_time(exam_item.duration)
            queue_time = generate_queue_time()
            
            # 计算叫号时间和完成时间
            call_time = check_time + timedelta(minutes=queue_time)
            finish_time = call_time + timedelta(minutes=service_time)
            
            # 创建记录
            record = QueueRecord(
                patient=patient,
                examination_item=exam_item,
                check_in_time=check_time,
                call_time=call_time,
                finish_time=finish_time,
                queue_time=queue_time,
                service_time=service_time,
                status='completed'  # 已完成状态
            )
            
            records_to_create.append(record)
            
            # 每1000条记录批量创建一次
            if len(records_to_create) >= 1000:
                with transaction.atomic():
                    QueueRecord.objects.bulk_create(records_to_create)
                records_to_create = []
                logger.info(f"已创建 {_+1} 条记录")
        
        # 创建剩余的记录
        if records_to_create:
            with transaction.atomic():
                QueueRecord.objects.bulk_create(records_to_create)
        
        logger.info("队列记录生成完成！")
        
        # 验证生成的记录数
        total_records = QueueRecord.objects.filter(
            check_in_time__gte=datetime.combine(start_date, datetime.min.time()),
            status='completed'
        ).count()
        
        logger.info(f"成功生成 {total_records} 条队列记录")
        
    except Exception as e:
        logger.error(f"生成队列记录时出错: {str(e)}")
        raise

if __name__ == '__main__':
    generate_queue_records() 