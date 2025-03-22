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

def delete_duplicate_records():
    """删除重复的病历号记录"""
    try:
        with connection.cursor() as cursor:
            # 找出重复的病历号
            cursor.execute("""
                SELECT medical_record_number, COUNT(*) as count
                FROM navigation_patient
                GROUP BY medical_record_number
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            
            if not duplicates:
                logger.info("没有找到重复的病历号")
                return
            
            for medical_record_number, count in duplicates:
                logger.info(f"发现重复病历号: {medical_record_number}, 重复次数: {count}")
                
                # 保留最早创建的记录，删除其他重复记录
                cursor.execute("""
                    DELETE FROM navigation_patient 
                    WHERE medical_record_number = %s 
                    AND id NOT IN (
                        SELECT id 
                        FROM (
                            SELECT id 
                            FROM navigation_patient 
                            WHERE medical_record_number = %s 
                            ORDER BY created_at ASC 
                            LIMIT 1
                        ) t
                    )
                """, [medical_record_number, medical_record_number])
                
                logger.info(f"已删除 {cursor.rowcount} 条重复记录")
            
            logger.info("重复记录清理完成")
            
    except Exception as e:
        logger.error(f"删除重复记录时出错: {str(e)}")
        raise

if __name__ == '__main__':
    delete_duplicate_records() 