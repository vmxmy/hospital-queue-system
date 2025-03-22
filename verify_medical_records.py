import os
import sys
import django
import logging
from datetime import datetime
from collections import Counter

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

from navigation.models import Patient

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_medical_records():
    """验证更新后的病历号"""
    try:
        # 获取所有病历号
        all_records = Patient.objects.values_list('medical_record_number', flat=True)
        total_count = len(all_records)
        
        # 检查重复
        duplicates = [item for item, count in Counter(all_records).items() if count > 1]
        
        # 日期范围验证
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2025, 3, 31)
        invalid_dates = []
        invalid_formats = []
        
        for record in all_records:
            try:
                # 验证格式
                if len(record) != 12:  # 应该是12位数字
                    invalid_formats.append(record)
                    continue
                    
                # 提取日期部分
                date_str = record[:8]
                date = datetime.strptime(date_str, '%Y%m%d')
                
                # 验证日期范围
                if date < start_date or date > end_date:
                    invalid_dates.append(record)
                    
            except ValueError:
                invalid_formats.append(record)
        
        # 输出验证结果
        logger.info(f"总记录数: {total_count}")
        
        if duplicates:
            logger.error(f"发现重复的病历号: {duplicates}")
        else:
            logger.info("未发现重复的病历号")
            
        if invalid_dates:
            logger.error(f"发现日期范围不正确的病历号: {invalid_dates}")
        else:
            logger.info("所有病历号的日期范围都正确")
            
        if invalid_formats:
            logger.error(f"发现格式不正确的病历号: {invalid_formats}")
        else:
            logger.info("所有病历号的格式都正确")
            
        if not (duplicates or invalid_dates or invalid_formats):
            logger.info("验证通过！所有病历号都符合要求")
            
    except Exception as e:
        logger.error(f"验证过程中出错: {str(e)}")
        raise

if __name__ == '__main__':
    verify_medical_records() 