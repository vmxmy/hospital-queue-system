import os
import sys
import django
import logging
from django.db import connection

# 设置Django环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def delete_conflict_record():
    """删除导致冲突的记录"""
    try:
        with connection.cursor() as cursor:
            # 找到医疗记录号为202503010008的记录
            cursor.execute("""
                SELECT id, medical_record_number, created_at
                FROM navigation_patient
                WHERE medical_record_number = '202503010008'
            """)
            record = cursor.fetchone()
            
            if not record:
                logger.info("未找到指定的记录")
                return
            
            # 删除该记录
            cursor.execute("""
                DELETE FROM navigation_patient
                WHERE id = %s
            """, [record[0]])
            
            logger.info(f"已删除病历号为 {record[1]} 的记录")
            
    except Exception as e:
        logger.error(f"删除记录时出错: {str(e)}")
        raise

if __name__ == '__main__':
    delete_conflict_record() 