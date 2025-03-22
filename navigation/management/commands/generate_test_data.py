import random
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from faker import Faker
from navigation.models import Patient, Department, Equipment, Examination, Queue

class Command(BaseCommand):
    help = '生成模拟测试数据：500条排队数据和2000条已完成检验数据'

    def add_arguments(self, parser):
        parser.add_argument('--queuing', type=int, default=500, help='生成排队中的记录数量')
        parser.add_argument('--completed', type=int, default=2000, help='生成已完成的记录数量')

    def handle(self, *args, **options):
        # 初始化Faker，用于生成中文假数据
        fake = Faker(['zh_CN'])
        
        # 获取参数
        queuing_count = options['queuing']
        completed_count = options['completed']

        # 获取已有数据
        departments = list(Department.objects.all())
        equipment_list = list(Equipment.objects.all())
        examinations = list(Examination.objects.all())
        
        if not departments or not equipment_list or not examinations:
            self.stdout.write(self.style.ERROR('数据库中没有足够的科室、设备或检查项目数据，请先创建这些基础数据'))
            return
        
        # 生成或获取足够的患者数据
        self.stdout.write(self.style.WARNING('开始生成患者数据...'))
        total_patients_needed = queuing_count + completed_count
        
        existing_patients = list(Patient.objects.all())
        existing_count = len(existing_patients)
        
        if existing_count < total_patients_needed:
            self.generate_patients(fake, total_patients_needed - existing_count)
        
        # 重新获取所有患者
        patients = list(Patient.objects.all())
        self.stdout.write(self.style.SUCCESS(f'现有患者数据: {len(patients)}'))
        
        # 生成排队数据
        with transaction.atomic():
            # 生成等待中的数据
            self.stdout.write(self.style.WARNING(f'开始生成{queuing_count}条排队中的记录...'))
            self.generate_queue_records(fake, patients, departments, equipment_list, examinations, queuing_count, 'waiting')
            
            # 生成已完成的数据
            self.stdout.write(self.style.WARNING(f'开始生成{completed_count}条已完成的记录...'))
            self.generate_queue_records(fake, patients, departments, equipment_list, examinations, completed_count, 'completed')
        
        self.stdout.write(self.style.SUCCESS('模拟数据生成完成！'))
    
    def generate_patients(self, fake, count):
        """生成指定数量的模拟患者数据"""
        self.stdout.write(self.style.WARNING(f'生成{count}个新患者...'))
        
        # 获取当前最大的病历号
        try:
            last_mrn = Patient.objects.order_by('-medical_record_number').first()
            if last_mrn and last_mrn.medical_record_number.startswith('P'):
                last_num = int(last_mrn.medical_record_number[1:])
            else:
                last_num = 20250000
        except (ValueError, AttributeError):
            last_num = 20250000
        
        batch_size = 500
        patients_created = 0
        
        # 批量创建患者以提高性能
        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            patient_batch = []
            
            for j in range(batch_count):
                # 随机生成性别
                gender = random.choice(['male', 'female'])
                
                # 生成出生日期
                birth_date = fake.date_of_birth(minimum_age=18, maximum_age=90)
                
                # 生成病历号
                mrn = f'P{last_num + i + j + 1}'
                
                # 生成优先级，大部分为普通
                priority = random.choices([0, 1, 2], weights=[0.85, 0.1, 0.05])[0]
                
                # 创建患者模型实例
                patient = Patient(
                    name=fake.name(),
                    gender=gender,
                    birth_date=birth_date,
                    id_number=fake.ssn(),
                    phone=fake.phone_number(),
                    address=fake.address(),
                    medical_record_number=mrn,
                    priority=priority,
                    special_needs='' if random.random() > 0.15 else fake.text(max_nb_chars=50),
                    medical_history='无' if random.random() > 0.3 else fake.text(max_nb_chars=100),
                    allergies='无' if random.random() > 0.2 else f'{fake.word()}过敏',
                    notes='' if random.random() > 0.2 else fake.text(max_nb_chars=50)
                )
                patient_batch.append(patient)
            
            # 批量创建
            Patient.objects.bulk_create(patient_batch)
            patients_created += batch_count
            self.stdout.write(self.style.SUCCESS(f'已创建 {patients_created}/{count} 个患者'))
    
    def generate_queue_records(self, fake, patients, departments, equipment_list, examinations, count, status):
        """生成指定状态的队列记录"""
        batch_size = 500
        records_created = 0
        
        # 计算日期范围
        now = timezone.now()
        if status == 'completed':
            # 对于已完成记录，使用过去90天内的随机时间
            date_start = now - datetime.timedelta(days=90)
        else:
            # 对于等待中记录，使用今天的时间
            date_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
        
        # 获取当前最大的队列号
        try:
            last_queue = Queue.objects.order_by('-id').first()
            if last_queue:
                last_queue_num = last_queue.id
            else:
                last_queue_num = 0
        except Exception:
            last_queue_num = 0
        
        # 批量创建队列记录
        for i in range(0, count, batch_size):
            batch_count = min(batch_size, count - i)
            queue_batch = []
            
            for j in range(batch_count):
                # 随机选择患者、科室、检查项目和设备
                patient = random.choice(patients)
                department = random.choice(departments)
                
                # 获取该科室的检查项目
                dept_examinations = [e for e in examinations if e.department_id == department.id]
                examination = random.choice(dept_examinations if dept_examinations else examinations)
                
                # 获取该科室的设备
                dept_equipment = [e for e in equipment_list if e.department_id == department.id]
                equipment = random.choice(dept_equipment if dept_equipment else equipment_list)
                
                # 设置优先级，大部分为普通，少部分为优先或紧急
                priority_weights = [0.8, 0.15, 0.05]  # 普通、优先、紧急的权重
                priority = random.choices([0, 1, 2], weights=priority_weights)[0]
                
                # 设置估计等待时间
                estimated_wait_time = random.randint(5, 60)
                
                # 生成唯一队列号
                queue_number = f"{department.code}{(last_queue_num + i + j + 1):04d}"
                
                # 创建队列记录实例
                queue = Queue(
                    patient=patient,
                    department=department,
                    examination=examination,
                    equipment=equipment,
                    queue_number=queue_number,  # 设置唯一队列号
                    status='waiting',  # 初始状态都是等待中
                    priority=priority,
                    estimated_wait_time=estimated_wait_time
                )
                
                if status == 'completed':
                    # 对于已完成的记录，设置时间戳
                    created_time = fake.date_time_between(start_date=date_start, end_date=now)
                    # 确保时间在工作时间内 (8:00 - 18:00)
                    created_time = created_time.replace(
                        hour=random.randint(8, 17),
                        minute=random.randint(0, 59),
                        second=random.randint(0, 59)
                    )
                    start_delta = datetime.timedelta(minutes=random.randint(5, 45))
                    start_time = created_time + start_delta
                    end_delta = datetime.timedelta(minutes=random.randint(10, 60))
                    end_time = start_time + end_delta
                    
                    # 设置队列记录的时间和状态
                    queue.created_at = created_time
                    queue.start_time = start_time
                    queue.end_time = end_time
                    queue.status = 'completed'  # 已完成状态
                    queue.actual_wait_time = int(start_delta.total_seconds() / 60)
                    
                    # 对于已完成记录，设置进入时间为创建时间
                    queue.enter_time = created_time
                else:
                    # 对于等待中记录，设置进入时间为当前时间
                    queue.enter_time = now
                
                queue_batch.append(queue)
            
            # 批量创建
            Queue.objects.bulk_create(queue_batch)
            records_created += batch_count
            self.stdout.write(self.style.SUCCESS(f'已创建 {records_created}/{count} 条{status}状态的队列记录')) 