import os
import sys
import django
import logging
import random
from datetime import datetime, timedelta
from django.db import connection, transaction
from django.db.utils import IntegrityError

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

from navigation.models import Patient

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_random_date():
    """生成2024年1月到2025年3月之间的随机日期"""
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2025, 3, 31)
    days_between = (end_date - start_date).days
    random_days = random.randint(0, days_between)
    random_date = start_date + timedelta(days=random_days)
    return random_date

def generate_new_medical_record_number(old_number, used_numbers):
    """生成新的病历号，确保不会与已使用的号码重复"""
    # 生成随机日期
    random_date = generate_random_date()
    
    # 获取序列号
    sequence = str(len(used_numbers) + 1).zfill(4)
    
    # 生成新号码
    new_number = f"{random_date.strftime('%Y%m%d')}{sequence}"
    
    # 如果新号码已被使用，尝试生成下一个序号
    attempts = 0
    while new_number in used_numbers and attempts < 1000:
        # 重新生成随机日期和序号
        random_date = generate_random_date()
        sequence = str(int(sequence) + 1).zfill(4)
        new_number = f"{random_date.strftime('%Y%m%d')}{sequence}"
        attempts += 1
        
    if attempts >= 1000:
        raise ValueError("无法生成唯一的新病历号")
        
    used_numbers.add(new_number)
    return new_number

def update_medical_record_numbers():
    """更新所有病人的病历号"""
    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                # 创建临时表来存储新旧病历号的映射
                cursor.execute("""
                    CREATE TEMPORARY TABLE temp_medical_records (
                        old_number VARCHAR(255) PRIMARY KEY,
                        new_number VARCHAR(255) UNIQUE
                    )
                """)
                
                # 获取所有现有的病历号
                cursor.execute("SELECT medical_record_number FROM navigation_patient ORDER BY created_at, id")
                existing_numbers = cursor.fetchall()
                
                # 用于跟踪已使用的新病历号
                used_numbers = set()
                total_count = len(existing_numbers)
                
                # 为每个病人生成新的病历号
                for i, (old_number,) in enumerate(existing_numbers, 1):
                    try:
                        new_number = generate_new_medical_record_number(old_number, used_numbers)
                        
                        # 将新旧病历号的映射插入临时表
                        cursor.execute("""
                            INSERT INTO temp_medical_records (old_number, new_number)
                            VALUES (%s, %s)
                        """, [old_number, new_number])
                        
                        logger.info(f"更新进度: {i}/{total_count}")
                        logger.info(f"生成新病历号 - 患者 {old_number}: {old_number} -> {new_number}")
                        
                    except Exception as e:
                        logger.error(f"处理病历号 {old_number} 时出错: {str(e)}")
                        raise
                
                # 使用临时表更新主表
                cursor.execute("""
                    UPDATE navigation_patient
                    SET medical_record_number = (
                        SELECT new_number
                        FROM temp_medical_records
                        WHERE temp_medical_records.old_number = navigation_patient.medical_record_number
                    )
                """)
                
                # 删除临时表
                cursor.execute("DROP TABLE temp_medical_records")
                
                logger.info("所有病历号更新完成")
                
    except Exception as e:
        logger.error(f"更新医疗记录号时出错: {str(e)}")
        raise

if __name__ == '__main__':
    update_medical_record_numbers() 