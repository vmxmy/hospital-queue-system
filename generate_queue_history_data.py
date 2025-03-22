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

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('data_generation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospitalLane.settings')
django.setup()

from navigation.models import Department, Equipment, Examination, Patient, Queue, QueueHistory
from django.db import transaction
from django.contrib.auth.models import User

# 初始化Faker
fake = Faker('zh_CN')
timezone.activate(pytz.timezone('Asia/Shanghai'))

def create_users(num_users=100):
    """创建用户数据"""
    users = []
    start_time = timezone.now()
    logger.info(f"开始创建 {num_users} 个用户...")
    
    try:
        for i in range(num_users):
            username = fake.user_name()
            if not User.objects.filter(username=username).exists():
                user = User.objects.create_user(
                    username=username,
                    email=fake.email(),
                    password='password123'
                )
                users.append(user)
            
            if (i + 1) % 100 == 0:
                logger.info(f"已创建 {i + 1} 个用户")
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        logger.info(f"用户创建完成，共创建 {len(users)} 个用户，耗时 {duration:.2f} 秒")
        
    except Exception as e:
        logger.error(f"创建用户时发生错误: {str(e)}")
        raise
    
    return users

def create_patients(num_patients=500, users=None):
    """创建患者数据"""
    start_time = timezone.now()
    logger.info(f"开始创建 {num_patients} 个患者...")
    
    used_users = set()  # 跟踪已使用的用户
    gender_choices = ['M', 'F']
    priority_choices = [0, 1, 2]  # 普通、优先、紧急
    priority_weights = [0.8, 0.15, 0.05]  # 80%普通，15%优先，5%紧急
    
    # 年龄分布 - 使用正态分布模拟真实人口年龄分布
    age_mean = 50
    age_std = 20
    
    # 批量创建，每批1000个
    batch_size = 1000
    total_created = 0
    
    try:
        for batch_start in range(0, num_patients, batch_size):
            batch_end = min(batch_start + batch_size, num_patients)
            patient_batch = []
            batch_start_time = timezone.now()
            
            logger.info(f"开始处理第 {batch_start//batch_size + 1} 批患者数据 ({batch_start+1} - {batch_end})")
            
            for _ in range(batch_start, batch_end):
                # 年龄采样，限制在0-100岁之间
                age = max(0, min(100, int(np.random.normal(age_mean, age_std))))
                birth_date = datetime.date.today() - datetime.timedelta(days=age*365)
                
                gender = random.choice(gender_choices)
                priority = random.choices(priority_choices, weights=priority_weights)[0]
                
                # 特殊需求的概率
                special_needs = ""
                if random.random() < 0.1:  # 10%的患者有特殊需求
                    needs = ["轮椅", "助行器", "翻译", "听力障碍", "视力障碍"]
                    special_needs = random.choice(needs)
                
                # 随机分配未使用的用户
                user = None
                if users and random.random() < 0.7:  # 70%的患者关联用户
                    available_users = [u for u in users if u.id not in used_users]
                    if available_users:
                        user = random.choice(available_users)
                        used_users.add(user.id)
                
                # 生成唯一的身份证号和病历号
                while True:
                    id_number = fake.ssn()
                    medical_record_number = fake.ean(length=13)
                    if not Patient.objects.filter(id_number=id_number).exists() and \
                       not Patient.objects.filter(medical_record_number=medical_record_number).exists():
                        break
                
                patient = Patient(
                    user=user,
                    name=fake.name(),
                    id_number=id_number,
                    gender=gender,
                    birth_date=birth_date,
                    phone=fake.phone_number(),
                    address=fake.address(),
                    medical_record_number=medical_record_number,
                    priority=priority,
                    special_needs=special_needs,
                    medical_history="" if random.random() < 0.7 else fake.text(max_nb_chars=100),
                    allergies="" if random.random() < 0.8 else random.choice(["青霉素", "磺胺类", "海鲜", "花粉", "乳制品"]),
                    notes="" if random.random() < 0.9 else fake.text(max_nb_chars=50)
                )
                patient_batch.append(patient)
            
            # 批量创建这一批患者
            Patient.objects.bulk_create(patient_batch)
            total_created += len(patient_batch)
            
            batch_duration = (timezone.now() - batch_start_time).total_seconds()
            logger.info(f"第 {batch_start//batch_size + 1} 批患者创建完成，"
                       f"本批创建 {len(patient_batch)} 个患者，"
                       f"耗时 {batch_duration:.2f} 秒，"
                       f"总计已创建 {total_created}/{num_patients} 个患者")
        
        end_time = timezone.now()
        total_duration = (end_time - start_time).total_seconds()
        logger.info(f"患者数据生成完成，共创建 {total_created} 个患者，总耗时 {total_duration:.2f} 秒")
        
    except Exception as e:
        logger.error(f"创建患者时发生错误: {str(e)}")
        raise
    
    return Patient.objects.all()

def generate_realistic_datetime(start_date, end_date):
    # 生成随机日期
    days = (end_date - start_date).days
    random_date = start_date + datetime.timedelta(days=random.randint(0, days))
    
    # 工作日权重更高
    if random_date.weekday() >= 5:  # 周末
        if random.random() < 0.6:  # 60%的概率重新选择日期(使工作日的检查量大于周末)
            return generate_realistic_datetime(start_date, end_date)
    
    # 考虑节假日因素（简化处理，实际应用可导入真实节假日数据）
    chinese_holidays = [
        # 2023年主要节假日
        datetime.date(2023, 1, 1),  # 元旦
        datetime.date(2023, 1, 22), datetime.date(2023, 1, 23), datetime.date(2023, 1, 24),  # 春节
        datetime.date(2023, 4, 5),  # 清明节
        datetime.date(2023, 5, 1),  # 劳动节
        datetime.date(2023, 6, 22), datetime.date(2023, 6, 23),  # 端午节
        datetime.date(2023, 9, 29), datetime.date(2023, 9, 30), datetime.date(2023, 10, 1),  # 中秋节+国庆节
        # 2024年主要节假日
        datetime.date(2024, 1, 1),  # 元旦
        datetime.date(2024, 2, 10), datetime.date(2024, 2, 11), datetime.date(2024, 2, 12),  # 春节
        datetime.date(2024, 4, 4),  # 清明节
        datetime.date(2024, 5, 1),  # 劳动节
        datetime.date(2024, 6, 10),  # 端午节
        datetime.date(2024, 9, 17),  # 中秋节
        datetime.date(2024, 10, 1),  # 国庆节
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
    
    return datetime.datetime.combine(random_date, datetime.time(hour, minute, second))

def generate_queue_history(num_records=10000):
    """生成队列历史记录"""
    start_time = timezone.now()
    logger.info(f"开始生成 {num_records} 条队列历史记录...")
    
    try:
        # 获取所有可用的数据
        departments = list(Department.objects.all())
        examinations = list(Examination.objects.all())
        equipments = list(Equipment.objects.all())
        patients = list(Patient.objects.all())
        
        logger.info(f"数据加载完成：")
        logger.info(f"- 科室数量: {len(departments)}")
        logger.info(f"- 检查项目数量: {len(examinations)}")
        logger.info(f"- 设备数量: {len(equipments)}")
        logger.info(f"- 患者数量: {len(patients)}")
        
        if not patients:
            logger.error("没有找到患者数据，请先创建患者")
            return []
        
        # 状态选项及其权重
        status_options = ['completed', 'cancelled', 'skipped']
        status_weights = [0.9, 0.07, 0.03]  # 90%完成，7%取消，3%跳过
        
        # 优先级及其权重
        priority_options = [0, 1, 2]  # 普通、优先、紧急
        priority_weights = [0.8, 0.15, 0.05]
        
        # 时间范围 - 过去一年
        end_date = timezone.now()
        start_date = end_date - datetime.timedelta(days=365)
        
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
            exam_equip_map[exam.id] = list(Equipment.objects.filter(department=exam.department))
        
        queue_objects = []
        history_objects = []
        queue_numbers = {dept.id: 1 for dept in departments}  # 按科室跟踪队列号
        
        batch_size = 1000
        total_created = 0
        
        # 批量创建记录
        for batch_start in range(0, num_records, batch_size):
            batch_end = min(batch_start + batch_size, num_records)
            batch_start_time = timezone.now()
            
            logger.info(f"开始处理第 {batch_start//batch_size + 1} 批队列记录 ({batch_start+1} - {batch_end})")
            
            with transaction.atomic():
                for _ in range(batch_start, batch_end):
                    # 选择随机科室，但考虑不同科室的实际检查量差异
                    department = random.choices(departments, weights=[100, 80, 120])[0]
                    
                    # 根据科室选择检查项目
                    possible_exams = dept_exam_map.get(department.id, [])
                    if not possible_exams:
                        continue
                    
                    # 科室内各检查项目权重
                    exam_weights = []
                    for exam in possible_exams:
                        if "常规" in exam.name or "X光" in exam.name:
                            weight = 10  # 常规检查更频繁
                        elif "动态" in exam.name:
                            weight = 3   # 特殊检查较少
                        else:
                            weight = 5   # 其他检查中等频率
                        exam_weights.append(weight)
                    
                    examination = random.choices(possible_exams, weights=exam_weights)[0]
                    
                    # 根据检查项目选择设备
                    possible_equips = exam_equip_map.get(examination.id, [])
                    if not possible_equips:
                        continue
                    
                    equipment = random.choice(possible_equips)
                    
                    # 选择随机患者
                    patient = random.choice(patients)
                    
                    # 生成符合实际分布的时间
                    enter_time = generate_realistic_datetime(start_date, end_date)
                    
                    # 进入时间、开始时间和结束时间的合理关系
                    wait_time_mean = department.average_service_time * (0.5 + random.random())
                    wait_time = max(1, int(np.random.normal(wait_time_mean, wait_time_mean/4)))
                    
                    start_time_local = enter_time + datetime.timedelta(minutes=wait_time)
                    
                    service_time_mean = examination.duration
                    service_time = max(1, int(np.random.normal(service_time_mean, service_time_mean/5)))
                    
                    exit_time_local = start_time_local + datetime.timedelta(minutes=service_time)
                    
                    # 根据状态调整开始和结束时间
                    status = random.choices(status_options, weights=status_weights)[0]
                    if status == 'cancelled':
                        start_time_local = None
                        exit_time_local = None
                    elif status == 'skipped':
                        exit_time_local = None
                    
                    # 计算等待时间和实际服务时间
                    estimated_wait_time = wait_time if status == 'completed' else None
                    actual_wait_time = wait_time if status == 'completed' else None
                    
                    # 分配队列号
                    queue_number = queue_numbers[department.id]
                    queue_numbers[department.id] += 1
                    
                    # 创建Queue对象
                    queue = Queue(
                        department=department,
                        examination=examination,
                        equipment=equipment,
                        patient=patient,
                        queue_number=f"{department.code}{queue_number:06d}",
                        status=status,
                        priority=random.choices(priority_options, weights=priority_weights)[0],
                        estimated_wait_time=estimated_wait_time,
                        enter_time=enter_time,
                        start_time=start_time_local,
                        exit_time=exit_time_local,
                        notes="" if random.random() < 0.9 else fake.text(max_nb_chars=30)
                    )
                    queue_objects.append(queue)
                    
                    # 创建QueueHistory对象
                    history = QueueHistory(
                        queue=queue,
                        department=department,
                        examination=examination,
                        equipment=equipment,
                        patient=patient,
                        queue_number=queue.queue_number,
                        status=status,
                        priority=queue.priority,
                        estimated_wait_time=estimated_wait_time,
                        actual_wait_time=actual_wait_time,
                        enter_time=enter_time,
                        start_time=start_time_local,
                        exit_time=exit_time_local,
                        notes=queue.notes,
                    )
                    history_objects.append(history)
                
                # 批量创建Queue记录
                Queue.objects.bulk_create(queue_objects)
                
                # 更新history对象中的queue关联
                for i, history in enumerate(history_objects):
                    history.queue = queue_objects[i]
                
                # 批量创建QueueHistory记录
                QueueHistory.objects.bulk_create(history_objects)
                
                total_created += len(history_objects)
                
                batch_duration = (timezone.now() - batch_start_time).total_seconds()
                logger.info(f"第 {batch_start//batch_size + 1} 批队列记录创建完成，"
                           f"本批创建 {len(history_objects)} 条记录，"
                           f"耗时 {batch_duration:.2f} 秒，"
                           f"总计已创建 {total_created}/{num_records} 条记录")
                
                # 清空批次列表
                queue_objects = []
                history_objects = []
        
        end_time = timezone.now()
        total_duration = (end_time - start_time).total_seconds()
        logger.info(f"队列历史记录生成完成，共创建 {total_created} 条记录，总耗时 {total_duration:.2f} 秒")
        
    except Exception as e:
        logger.error(f"生成队列历史记录时发生错误: {str(e)}")
        raise
    
    return total_created

def main():
    """主函数"""
    total_start_time = timezone.now()
    logger.info("开始生成模拟数据...")
    
    try:
        # 创建更多用户以支持更大数量的患者
        users = create_users(num_users=2000)
        
        # 创建大量患者
        patients = create_patients(num_patients=200000, users=users)
        
        # 分批生成队列历史记录
        total_records = 1000000
        records_created = generate_queue_history(num_records=total_records)
        
        total_duration = (timezone.now() - total_start_time).total_seconds()
        logger.info("数据生成完成！")
        logger.info(f"总计：")
        logger.info(f"- 用户数量：{len(users)}")
        logger.info(f"- 患者数量：{Patient.objects.count()}")
        logger.info(f"- 队列历史记录：{records_created}")
        logger.info(f"总耗时：{total_duration:.2f} 秒")
        
    except Exception as e:
        logger.error(f"数据生成过程中发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    main() 