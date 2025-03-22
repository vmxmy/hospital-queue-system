import os
import django
import logging
from django.db import transaction
from datetime import datetime
from django.contrib.auth import get_user_model

# 设置Django环境为生产环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

# 导入模型
from navigation.models import (
    Patient,
    Department,
    Equipment,
    Examination,
    Queue,
    QueueHistory,
    NotificationTemplate,
    NotificationCategory,
    NotificationStats,
    NotificationTemplateVersion
)

# 设置日志
log_filename = f'data_clear_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_filename)
    ]
)
logger = logging.getLogger(__name__)

def backup_data():
    """备份数据库"""
    try:
        from django.conf import settings
        backup_file = f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.sql'
        
        db_settings = settings.DATABASES['default']
        host = db_settings.get('HOST', 'localhost')
        port = db_settings.get('PORT', '3306')
        name = db_settings.get('NAME')
        user = db_settings.get('USER')
        password = db_settings.get('PASSWORD')
        
        if all([name, user, password]):
            cmd = f'mysqldump -h {host} -P {port} -u {user} -p"{password}" {name} > {backup_file}'
            result = os.system(cmd)
            if result == 0:
                logger.info(f"数据库已备份到文件: {backup_file}")
                return True
            else:
                logger.error("数据库备份失败")
                return False
        
        logger.error("无法获取数据库配置信息")
        return False
    except Exception as e:
        logger.error(f"备份过程中发生错误: {str(e)}")
        return False

def confirm_operation(message="此操作将清除数据！"):
    """通用确认操作提示"""
    print(f"\n警告：{message}")
    print("\n此操作不可逆！请确保已经进行了数据备份。")
    print("\n请输入 'YES' (全大写) 确认继续操作: ")
    confirmation = input().strip()
    
    if confirmation != "YES":
        print("操作已取消")
        return False
        
    return True

def clear_queue_data():
    """清理所有队列和队列历史数据，但保留科室、设备、检查项目和患者基础数据"""
    # 检查是否确认清理操作
    if not confirm_operation("此操作将清除所有检查队列数据，包括等待中和历史记录的队列！"):
        return

    try:
        with transaction.atomic():
            # 删除队列历史记录
            queue_history_count = QueueHistory.objects.all().count()
            QueueHistory.objects.all().delete()
            logger.info(f"已删除 {queue_history_count} 条队列历史记录")
            
            # 删除当前队列数据
            queue_count = Queue.objects.all().count()
            Queue.objects.all().delete()
            logger.info(f"已删除 {queue_count} 条当前队列记录")

            logger.info("队列数据清理完成！")

    except Exception as e:
        logger.error(f"清理队列数据时发生错误: {str(e)}")
        raise

def clear_non_admin_users():
    """清理除admin以外的所有用户数据"""
    # 检查是否确认清理生产环境
    if not confirm_operation("此操作将清除所有非管理员用户数据！"):
        return

    # 先进行备份
    if not backup_data():
        logger.error("备份失败，为安全起见，取消清理操作")
        return

    User = get_user_model()
    
    try:
        with transaction.atomic():
            # 获取所有非超级用户的用户
            non_admin_users = User.objects.filter(is_superuser=False)
            count = non_admin_users.count()
            non_admin_users.delete()
            logger.info(f"已删除 {count} 个非管理员用户")

            logger.info("用户数据清理完成！")

    except Exception as e:
        logger.error(f"清理数据时发生错误: {str(e)}")
        raise

if __name__ == "__main__":
    # 根据需要选择要执行的操作
    print("请选择要执行的操作:")
    print("1. 清除所有队列数据（保留科室等基础数据）")
    print("2. 清除非管理员用户")
    print("0. 取消操作")
    
    choice = input("请输入选项编号: ").strip()
    
    if choice == "1":
        clear_queue_data()
    elif choice == "2":
        clear_non_admin_users()
    else:
        print("操作已取消") 