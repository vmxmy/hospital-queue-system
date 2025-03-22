import os
import django
import random
import datetime
import numpy as np
from faker import Faker
import pytz
from django.utils import timezone
import logging
import sys
from datetime import timedelta
from tqdm import tqdm
from django.db.models.signals import post_save, post_delete

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('queue_history_generation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospitalLane.settings')
django.setup()

from navigation.models import Department, Equipment, Examination, Patient, Queue, QueueHistory
from navigation.models.queue_history import QueueHistory
from django.db import transaction
from django.contrib.auth.models import User

# 初始化Faker
fake = Faker('zh_CN')
timezone.activate(pytz.timezone('Asia/Shanghai'))

# 生成真实世界分布的等待时间
def generate_wait_time_for_department(dept_name, num_patients_ahead, priority):
    """
    根据科室名称、队列前面的人数和优先级生成真实的等待时间
    
    参数:
    - dept_name: 科室名称
    - num_patients_ahead: 队列中前面的人数
    - priority: 优先级(0-3)
    
    返回:
    - 等待时间(分钟)
    """
    # 科室基准等待时间(分钟/人)
    dept_base_times = {
        "放射科": 10,
        "核医学科": 15,
        "超声科": 12,
        "内窥镜室": 20,
        "心电图室": 8,
        "脑电图室": 25,
        "临床实验室": 5,
        "病理科": 30
    }
    
    # 获取科室的基准等待时间，如果科室不在映射中则使用默认值15
    base_time = dept_base_times.get(dept_name, 15)
    
    # 生成基础等待时间
    # 1. 基础等待时间与队列前面的人数成正比
    base_wait = num_patients_ahead * base_time
    
    # 2. 波动因子 - 为等待时间添加随机波动，模拟真实情况
    # 平均值为1.0，标准差为0.3的正态分布，限制在0.5-2.0之间
    fluctuation = max(0.5, min(2.0, np.random.normal(1.0, 0.3)))
    
    # 3. 优先级调整因子 - 优先级越高，等待时间越短
    priority_factor = 1.0 / (1.0 + priority * 0.5)  # 优先级0: 1.0, 优先级1: 0.67, 优先级2: 0.5, 优先级3: 0.4
    
    # 4. 高峰期调整 - 特定时间段(上午9-11点，下午2-4点)等待时间通常更长
    time_factor = 1.0  # 默认时间因子
    
    # 5. 计算最终等待时间
    wait_time = int(base_wait * fluctuation * priority_factor * time_factor)
    
    # 6. 添加小的随机波动(±20%)，使数据更自然
    random_variance = random.uniform(0.8, 1.2)
    wait_time = int(wait_time * random_variance)
    
    # 确保等待时间在合理范围内
    # 即使是空队列，也需要一些处理时间
    wait_time = max(5, wait_time)
    
    # 极长的等待时间不太现实
    max_reasonable_wait = 240  # 4小时
    wait_time = min(wait_time, max_reasonable_wait)
    
    return wait_time

# 生成真实世界分布的检查用时
def generate_service_time(examination_name, patient_priority, patient_special_needs):
    """
    生成检查的服务时间
    
    参数:
    - examination_name: 检查名称
    - patient_priority: 患者优先级
    - patient_special_needs: 患者特殊需求
    
    返回:
    - 服务时间(分钟)
    """
    # 基准检查时间
    base_times = {
        "X光检查": random.randint(5, 15),
        "CT检查": random.randint(15, 30),
        "MRI检查": random.randint(30, 60),
        "超声检查": random.randint(15, 30),
        "心电图": random.randint(10, 20),
        "脑电图": random.randint(30, 60),
        "骨密度检查": random.randint(10, 20),
        "内窥镜检查": random.randint(20, 45),
        "PET-CT检查": random.randint(60, 120),
    }
    
    # 如果检查名称包含某些关键字，尝试匹配基准时间
    service_time = None
    for key, time_range in base_times.items():
        if key in examination_name:
            service_time = time_range
            break
    
    # 如果没有匹配到，使用默认的随机范围
    if service_time is None:
        service_time = random.randint(10, 40)  
    
    # 根据患者优先级调整服务时间（紧急情况可能服务更快）
    if patient_priority > 0:
        service_time = int(service_time * 0.9)  # 紧急情况服务时间可能减少10%
    
    # 特殊需求患者可能需要更长时间
    if patient_special_needs:
        service_time = int(service_time * 1.2)  # 增加20%的服务时间
    
    # 添加随机波动
    fluctuation = random.uniform(0.9, 1.1)  # ±10%的随机波动
    service_time = int(service_time * fluctuation)
    
    # 确保服务时间至少为5分钟
    return max(5, service_time)

# 生成真实的日期时间，考虑工作日、周末和节假日
def generate_realistic_datetime(start_date, end_date):
    # 生成随机日期
    time_span = (end_date - start_date).days
    random_days = random.randint(0, time_span)
    random_date = start_date + timedelta(days=random_days)
    
    # 工作日权重更高
    if random_date.weekday() >= 5:  # 周末
        if random.random() < 0.6:  # 60%的概率重新选择日期(使工作日的检查量大于周末)
            return generate_realistic_datetime(start_date, end_date)
    
    # 考虑节假日因素（简化处理，实际应用可导入真实节假日数据）
    chinese_holidays = [
        # 2024年主要节假日
        datetime.date(2024, 1, 1),  # 元旦
        datetime.date(2024, 2, 10), datetime.date(2024, 2, 11), datetime.date(2024, 2, 12),  # 春节
        datetime.date(2024, 4, 4),  # 清明节
        datetime.date(2024, 5, 1),  # 劳动节
        datetime.date(2024, 6, 10),  # 端午节
        datetime.date(2024, 9, 17),  # 中秋节
        datetime.date(2024, 10, 1),  # 国庆节
        # 2025年主要节假日
        datetime.date(2025, 1, 1),  # 元旦
        datetime.date(2025, 1, 29), datetime.date(2025, 1, 30), datetime.date(2025, 1, 31),  # 春节
        datetime.date(2025, 4, 4),  # 清明节
        datetime.date(2025, 5, 1),  # 劳动节
        datetime.date(2025, 6, 2),  # 端午节
        datetime.date(2025, 10, 1),  # 国庆节
    ]
    
    if random_date.date() in chinese_holidays:
        if random.random() < 0.8:  # 80%的概率重新选择日期
            return generate_realistic_datetime(start_date, end_date)
    
    # 生成时间（8:00-17:00之间，上午几率更高）
    hour_weights = [0, 0, 0, 0, 0, 0, 0, 0,
                   5, 10, 10, 10, 8,  # 8-12点（上午）权重高
                   5, 7, 7, 7, 5,     # 13-17点（下午）权重稍低
                   0, 0, 0, 0, 0, 0]
    
    hour = random.choices(range(24), weights=hour_weights)[0]
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return datetime.datetime.combine(random_date, datetime.time(hour, minute, second)).replace(tzinfo=pytz.timezone('Asia/Shanghai'))

# 临时禁用信号的上下文管理器
class DisableSignals:
    def __init__(self, disabled_signals=None):
        self.disabled_signals = disabled_signals or [post_save, post_delete]
        self.stashed_signals = {}
        self.receivers = []
        
    def __enter__(self):
        for signal in self.disabled_signals:
            self.receivers.extend(signal.receivers)
            self.stashed_signals[signal] = signal.receivers
            signal.receivers = []
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        for signal, receivers in self.stashed_signals.items():
            signal.receivers = receivers

# 主函数：生成队列历史数据
def generate_queue_history_for_ml(num_records=10000):
    """
    生成队列历史记录用于机器学习训练
    
    参数:
    - num_records: 要生成的记录数量
    
    返回:
    - 生成的记录列表
    """
    start_time = timezone.now()
    logger.info(f"开始生成 {num_records} 条队列历史记录...")
    
    try:
        # 获取所有可用的数据
        departments = list(Department.objects.all())
        examinations = list(Examination.objects.all())
        equipments = list(Equipment.objects.all())
        patients = list(Patient.objects.all())
        
        if not departments or not examinations or not equipments or not patients:
            logger.error("基础数据不足，请确保系统中已有科室、检查项目、设备和患者数据")
            return []
        
        logger.info(f"数据加载完成：")
        logger.info(f"- 科室数量: {len(departments)}")
        logger.info(f"- 检查项目数量: {len(examinations)}")
        logger.info(f"- 设备数量: {len(equipments)}")
        logger.info(f"- 患者数量: {len(patients)}")
        
        # 设置时间范围: 2024年1月 - 2025年3月
        start_date = datetime.datetime(2024, 1, 1, tzinfo=pytz.timezone('Asia/Shanghai'))
        end_date = datetime.datetime(2025, 3, 31, tzinfo=pytz.timezone('Asia/Shanghai'))
        
        # 建立科室和检查项目的映射
        dept_exam_map = {}
        for exam in examinations:
            if exam.department_id not in dept_exam_map:
                dept_exam_map[exam.department_id] = []
            dept_exam_map[exam.department_id].append(exam)
        
        # 建立科室和设备的映射
        dept_equip_map = {}
        for equip in equipments:
            if equip.department_id not in dept_equip_map:
                dept_equip_map[equip.department_id] = []
            dept_equip_map[equip.department_id].append(equip)
        
        # 批量创建历史记录
        batch_size = 100
        created_count = 0
        
        logger.info(f"开始生成队列历史记录...")
        
        # 临时禁用信号
        with DisableSignals():
            for i in tqdm(range(num_records), desc="生成队列历史记录"):
                try:
                    with transaction.atomic():
                        # 随机选择病人
                        patient = random.choice(patients)
                        
                        # 随机选择科室
                        department = random.choice(departments)
                        
                        # 从该科室的检查项目中随机选择
                        available_exams = dept_exam_map.get(department.id, [])
                        if not available_exams:
                            continue
                        examination = random.choice(available_exams)
                        
                        # 从该科室的设备中随机选择
                        available_equips = dept_equip_map.get(department.id, [])
                        equipment = random.choice(available_equips) if available_equips else None
                        
                        # 生成合理的日期时间
                        enter_time = generate_realistic_datetime(start_date, end_date)
                        
                        # 决定患者优先级 - 大多数是普通优先级
                        priority_options = [0, 1, 2, 3]  # 普通、优先、紧急、危急
                        priority_weights = [0.8, 0.15, 0.04, 0.01]  # 大多数是普通优先级
                        priority = random.choices(priority_options, weights=priority_weights)[0]
                        
                        # 生成队列前面的人数 - 模拟真实排队情况
                        # 早上通常人更多，周一周二通常更忙
                        hour_of_day = enter_time.hour
                        day_of_week = enter_time.weekday()
                        
                        # 根据时间计算基础队列人数
                        base_queue_count = 0
                        if 8 <= hour_of_day <= 11:  # 早上繁忙时段
                            base_queue_count = random.randint(10, 50)
                        elif 13 <= hour_of_day <= 15:  # 下午繁忙时段
                            base_queue_count = random.randint(5, 30)
                        else:  # 其他时段
                            base_queue_count = random.randint(0, 15)
                        
                        # 周一周二通常更忙
                        if day_of_week < 2:
                            base_queue_count = int(base_queue_count * 1.3)
                        
                        # 考虑优先级影响（高优先级的人可能在插队的情况下，排在更前面）
                        if priority > 0:
                            base_queue_count = int(base_queue_count * (1 - priority * 0.2))
                        
                        # 确保队列人数非负
                        num_patients_ahead = max(0, base_queue_count)
                        
                        # 生成估计等待时间
                        estimated_wait_time = generate_wait_time_for_department(department.name, num_patients_ahead, priority)
                        
                        # 生成实际等待时间（添加一些随机波动）
                        # 实际等待时间通常与估计等待时间有一定差距
                        accuracy = random.uniform(0.8, 1.2)  # 预测准确度在80%-120%之间浮动
                        actual_wait_time = int(estimated_wait_time * accuracy)
                        actual_wait_time = max(1, actual_wait_time)  # 确保至少等待1分钟
                        
                        # 计算开始时间和结束时间
                        start_time_dt = enter_time + timedelta(minutes=actual_wait_time)
                        
                        # 生成检查用时
                        service_time = generate_service_time(examination.name, priority, patient.special_needs)
                        
                        # 计算结束时间
                        end_time_dt = start_time_dt + timedelta(minutes=service_time)
                        
                        # 1. 首先创建Queue对象
                        queue = Queue(
                            patient=patient,
                            department=department,
                            equipment=equipment,
                            examination=examination,
                            status='completed',
                            priority=priority,
                            estimated_wait_time=estimated_wait_time,
                            actual_wait_time=actual_wait_time,
                            enter_time=enter_time,
                            start_time=start_time_dt,
                            end_time=end_time_dt,
                            notes=f"系统生成的历史队列（用于训练），当时排队人数：{num_patients_ahead}"
                        )
                        queue.save()  # 先保存队列对象，以获取队列ID
                        
                        # 2. 然后基于Queue创建QueueHistory对象
                        queue_history = QueueHistory.create_from_queue(queue)
                        
                        created_count += 1
                        
                        if created_count % 100 == 0:
                            logger.info(f"已创建 {created_count} 条队列历史记录")
                
                except Exception as e:
                    logger.error(f"创建第 {i+1} 条记录时发生错误: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"队列历史记录生成完成，共创建 {created_count} 条记录，耗时 {duration:.2f} 秒")
        
    except Exception as e:
        logger.error(f"生成队列历史记录时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return 0
    
    return created_count

if __name__ == "__main__":
    logger.info("开始生成队列历史数据")
    records_count = generate_queue_history_for_ml(10000)
    logger.info(f"成功生成 {records_count} 条队列历史记录") 