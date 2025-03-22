import os
import sys
import django
import random
import logging
from datetime import datetime, timedelta
from django.utils import timezone
import numpy as np

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

from navigation.models import (
    Patient, Department, Equipment, Examination,
    Queue, QueueHistory
)

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_queue_number(department_code, patient_name):
    """生成队列号"""
    now = timezone.now()
    date_str = now.strftime("%Y%m%d")
    time_str = now.strftime("%H%M%S")
    import hashlib
    name_hash = hashlib.md5(patient_name.encode('utf-8')).hexdigest()[-4:]
    return f"{department_code}{date_str}{time_str}{name_hash}"

def generate_realistic_datetime(start_date, end_date, is_waiting=False):
    """生成真实的日期时间"""
    if is_waiting:
        # 对于等待中的记录，生成最近24小时内的时间
        start_date = timezone.now() - timedelta(hours=24)
        end_date = timezone.now()
    
    # 生成基础随机时间
    time_between = end_date - start_date
    days_between = time_between.days
    random_days = random.randint(0, days_between)
    random_date = start_date + timedelta(days=random_days)
    
    # 生成工作时间（8:00-18:00）
    hour = random.randint(8, 17)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    return random_date.replace(hour=hour, minute=minute, second=second)

def generate_queue_records(total_records=5000, waiting_records=500):
    """生成队列记录"""
    logger.info(f"开始生成 {total_records} 条队列记录（其中 {waiting_records} 条等待中）...")
    
    try:
        # 获取所有可用的数据
        departments = list(Department.objects.all())
        examinations = list(Examination.objects.all())
        equipments = list(Equipment.objects.filter(status='available'))
        patients = list(Patient.objects.all())
        
        if not all([departments, examinations, equipments, patients]):
            logger.error("缺少必要的基础数据，请确保已创建科室、检查项目、设备和患者数据")
            return
        
        logger.info(f"数据加载完成：")
        logger.info(f"- 科室数量: {len(departments)}")
        logger.info(f"- 检查项目数量: {len(examinations)}")
        logger.info(f"- 可用设备数量: {len(equipments)}")
        logger.info(f"- 患者数量: {len(patients)}")
        
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
        
        # 建立检查项目和设备的映射
        exam_equip_map = {}
        for exam in examinations:
            exam_equip_map[exam.id] = []
            for equip in equipments:
                if equip.department_id == exam.department_id:
                    exam_equip_map[exam.id].append(equip)
        
        # 优先级及其权重
        priority_options = [0, 1, 2, 3]  # 正常、加急、紧急、危急
        priority_weights = [0.7, 0.2, 0.07, 0.03]
        
        # 生成等待中的记录
        logger.info("开始生成等待中的记录...")
        waiting_queues = []
        for _ in range(waiting_records):
            try:
                # 选择随机科室
                department = random.choice(departments)
                
                # 根据科室选择检查项目
                possible_exams = dept_exam_map.get(department.id, [])
                if not possible_exams:
                    continue
                examination = random.choice(possible_exams)
                
                # 根据检查项目选择设备（可以为空）
                possible_equips = exam_equip_map.get(examination.id, [])
                equipment = random.choice(possible_equips) if possible_equips and random.random() > 0.3 else None
                
                # 选择随机患者
                patient = random.choice(patients)
                
                # 生成优先级
                priority = random.choices(priority_options, weights=priority_weights)[0]
                
                # 创建队列记录
                queue = Queue(
                    patient=patient,
                    department=department,
                    examination=examination,
                    equipment=equipment,
                    queue_number=generate_queue_number(department.code, patient.name),
                    status='waiting',
                    priority=priority,
                    enter_time=generate_realistic_datetime(
                        timezone.now() - timedelta(hours=24),
                        timezone.now(),
                        is_waiting=True
                    )
                )
                
                # 计算预计等待时间
                queue.estimated_wait_time = queue.estimate_initial_wait_time()
                queue.save()
                waiting_queues.append(queue)
                
            except Exception as e:
                logger.error(f"生成等待中记录时出错: {str(e)}")
                continue
        
        logger.info(f"成功生成 {len(waiting_queues)} 条等待中的记录")
        
        # 生成已完成的记录
        completed_records = total_records - waiting_records
        logger.info(f"开始生成 {completed_records} 条已完成的记录...")
        completed_queues = []
        
        # 设置时间范围 - 过去30天
        end_date = timezone.now() - timedelta(hours=1)  # 留出1小时的缓冲
        start_date = end_date - timedelta(days=30)
        
        for _ in range(completed_records):
            try:
                # 选择随机科室
                department = random.choice(departments)
                
                # 根据科室选择检查项目
                possible_exams = dept_exam_map.get(department.id, [])
                if not possible_exams:
                    continue
                examination = random.choice(possible_exams)
                
                # 根据检查项目选择设备
                possible_equips = exam_equip_map.get(examination.id, [])
                equipment = random.choice(possible_equips) if possible_equips and random.random() > 0.3 else None
                
                # 选择随机患者
                patient = random.choice(patients)
                
                # 生成优先级
                priority = random.choices(priority_options, weights=priority_weights)[0]
                
                # 生成时间
                enter_time = generate_realistic_datetime(start_date, end_date)
                
                # 根据检查项目时长和优先级计算服务时间
                base_duration = examination.duration
                priority_factor = max(0.8, 1 - (priority * 0.1))  # 优先级越高，等待时间越短
                wait_time = int(base_duration * (1 + random.random()) * priority_factor)
                
                start_time = enter_time + timedelta(minutes=wait_time)
                end_time = start_time + timedelta(minutes=base_duration)
                
                # 创建队列记录
                queue = Queue(
                    patient=patient,
                    department=department,
                    examination=examination,
                    equipment=equipment,
                    queue_number=generate_queue_number(department.code, patient.name),
                    status='completed',
                    priority=priority,
                    estimated_wait_time=wait_time,
                    actual_wait_time=wait_time,
                    enter_time=enter_time,
                    start_time=start_time,
                    end_time=end_time
                )
                queue.save()
                completed_queues.append(queue)
                
                # 创建历史记录
                QueueHistory.create_from_queue(queue)
                
            except Exception as e:
                logger.error(f"生成已完成记录时出错: {str(e)}")
                continue
        
        logger.info(f"成功生成 {len(completed_queues)} 条已完成的记录")
        logger.info("数据生成完成！")
        
    except Exception as e:
        logger.error(f"生成队列记录时出错: {str(e)}")

if __name__ == '__main__':
    generate_queue_records() 