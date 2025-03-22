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

def check_duplicate_patients():
    """检查完全重复的患者记录"""
    try:
        with connection.cursor() as cursor:
            # 检查所有字段都相同的记录
            cursor.execute("""
                SELECT 
                    p1.id,
                    p1.name,
                    p1.medical_record_number,
                    p1.created_at,
                    COUNT(*) as duplicate_count
                FROM navigation_patient p1
                JOIN navigation_patient p2 ON
                    p1.name = p2.name AND
                    p1.medical_record_number = p2.medical_record_number AND
                    p1.id != p2.id
                GROUP BY 
                    p1.id,
                    p1.name,
                    p1.medical_record_number,
                    p1.created_at
                HAVING COUNT(*) >= 1
                ORDER BY p1.created_at;
            """)
            
            duplicates = cursor.fetchall()
            
            if not duplicates:
                logger.info("未发现完全重复的患者记录")
                return
            
            logger.info(f"发现 {len(duplicates)} 组重复记录：")
            for record in duplicates:
                logger.info(f"ID: {record[0]}, 姓名: {record[1]}, " 
                          f"病历号: {record[2]}, 创建时间: {record[3]}, "
                          f"重复次数: {record[4]}")
            
    except Exception as e:
        logger.error(f"检查重复记录时出错: {str(e)}")
        raise

if __name__ == '__main__':
    check_duplicate_patients() 