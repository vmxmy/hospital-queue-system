#!/usr/bin/env python
import os
import sys
import django
import random
import time
from datetime import datetime, timedelta
import threading
import termios
import tty
import signal

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospital_queue.settings')
django.setup()

from navigation.models import Patient, Examination, Department, Queue
from django.utils import timezone
from django.db.models import Q

class MockQueueGenerator:
    """模拟队列生成器"""

    def __init__(self, interval=10):
        """
        初始化生成器
        
        参数:
        - interval: 生成新队列的时间间隔（秒）
        """
        self.interval = interval
        self.departments = None
        self.patients = None
        self.examinations = None
        self.is_running = True
        self.is_paused = False
        self._original_terminal_settings = None
        
    def setup_keyboard_control(self):
        """设置键盘控制"""
        if not sys.stdin.isatty():
            print("警告: 当前环境不支持键盘控制，将使用 Ctrl+C 来退出程序")
            return
            
        try:
            # 保存终端原始设置
            self._original_terminal_settings = termios.tcgetattr(sys.stdin)
            # 设置终端为原始模式
            tty.setraw(sys.stdin.fileno())
            
            # 创建键盘监听线程
            self.keyboard_thread = threading.Thread(target=self._keyboard_listener)
            self.keyboard_thread.daemon = True
            self.keyboard_thread.start()
        except Exception as e:
            print(f"警告: 设置键盘控制失败: {str(e)}")
            print("将使用 Ctrl+C 来退出程序")
            self._original_terminal_settings = None
        
    def restore_terminal(self):
        """恢复终端设置"""
        if self._original_terminal_settings:
            try:
                termios.tcsetattr(
                    sys.stdin, 
                    termios.TCSADRAIN, 
                    self._original_terminal_settings
                )
            except Exception as e:
                print(f"警告: 恢复终端设置失败: {str(e)}")
        
    def _keyboard_listener(self):
        """键盘监听处理"""
        try:
            while self.is_running:
                if sys.stdin.isatty():
                    char = sys.stdin.read(1)
                    
                    # Ctrl+S: 暂停/继续
                    if char == '\x13':
                        self.is_paused = not self.is_paused
                        status = "暂停" if self.is_paused else "继续"
                        print(f"\n队列生成已{status}")
                    
                    # Ctrl+Q: 退出
                    elif char == '\x11':
                        self.is_running = False
                        print("\n正在停止队列生成...")
                        break
                        
        except Exception as e:
            print(f"\n键盘监听出错: {str(e)}")
        finally:
            self.restore_terminal()
            
    def load_data(self):
        """加载必要的数据"""
        # 获取所有启用的科室
        self.departments = Department.objects.filter(is_active=True)
        if not self.departments.exists():
            raise ValueError("没有找到启用的科室")
            
        # 获取所有患者
        self.patients = Patient.objects.all()
        if not self.patients.exists():
            raise ValueError("没有找到患者数据")
            
        # 获取所有检查项目
        self.examinations = Examination.objects.filter(is_active=True)
        if not self.examinations.exists():
            raise ValueError("没有找到启用的检查项目")
    
    def get_random_patient(self):
        """随机获取一个没有活动队列的患者"""
        # 获取所有没有活动队列的患者
        available_patients = self.patients.exclude(
            Q(queue__status='waiting') | Q(queue__status='processing')
        ).distinct()
        
        if not available_patients.exists():
            return None
            
        return random.choice(available_patients)
    
    def get_random_examination(self, department=None):
        """
        随机获取一个检查项目
        
        参数:
        - department: 指定科室（可选）
        """
        examinations = self.examinations
        if department:
            examinations = examinations.filter(department=department)
            
        if not examinations.exists():
            return None
            
        return random.choice(examinations)
    
    def create_queue(self):
        """创建一个新的模拟队列"""
        try:
            # 随机获取一个患者
            patient = self.get_random_patient()
            if not patient:
                print("没有可用的患者")
                return None
                
            # 随机获取一个科室
            department = random.choice(self.departments)
            
            # 获取该科室的随机检查项目
            examination = self.get_random_examination(department)
            if not examination:
                print(f"科室 {department.name} 没有可用的检查项目")
                return None
            
            # 创建队列
            queue = Queue(
                patient=patient,
                department=department,
                examination=examination,
                priority=patient.priority,
                status='waiting'
            )
            
            # 保存队列（会自动生成队列号和预估等待时间）
            queue.save()
            
            print(f"创建新队列: {queue.queue_number} - 患者: {patient.name} - "
                  f"科室: {department.name} - 检查: {examination.name} - "
                  f"预计等待时间: {queue.estimated_wait_time}分钟")
            
            return queue
            
        except Exception as e:
            print(f"创建队列时出错: {str(e)}")
            return None
    
    def update_queue_status(self):
        """更新队列状态"""
        try:
            # 获取所有等待中的队列
            waiting_queues = Queue.objects.filter(status='waiting')
            
            for queue in waiting_queues:
                # 如果队列已经等待超过预计时间的 80%，有 30% 的概率开始处理
                if (timezone.now() - queue.enter_time).total_seconds() / 60 > queue.estimated_wait_time * 0.8:
                    if random.random() < 0.3:
                        queue.update_status('processing')
                        print(f"队列 {queue.queue_number} 开始处理")
                
            # 获取所有处理中的队列
            processing_queues = Queue.objects.filter(status='processing')
            
            for queue in processing_queues:
                # 如果队列已经处理超过检查时间，有 50% 的概率完成
                if queue.start_time and (timezone.now() - queue.start_time).total_seconds() / 60 > queue.examination.duration:
                    if random.random() < 0.5:
                        queue.update_status('completed')
                        print(f"队列 {queue.queue_number} 已完成")
                        
        except Exception as e:
            print(f"更新队列状态时出错: {str(e)}")
    
    def run(self):
        """运行生成器"""
        print("开始生成模拟队列...")
        print("控制说明:")
        print("- Ctrl+S: 暂停/继续生成")
        print("- Ctrl+Q: 退出程序")
        print("- Ctrl+C: 强制退出程序")
        
        self.load_data()
        self.setup_keyboard_control()
        
        try:
            while self.is_running:
                if not self.is_paused:
                    # 创建新队列
                    self.create_queue()
                    
                    # 更新现有队列状态
                    self.update_queue_status()
                
                # 等待指定时间
                time.sleep(self.interval)
                
        except Exception as e:
            print(f"运行时出错: {str(e)}")
        finally:
            self.restore_terminal()

def signal_handler(signum, frame):
    """信号处理函数"""
    print("\n收到退出信号，正在停止...")
    sys.exit(0)

if __name__ == '__main__':
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 默认每 10 秒生成一个新队列
    interval = 10
    if len(sys.argv) > 1:
        try:
            interval = int(sys.argv[1])
        except ValueError:
            print(f"无效的时间间隔: {sys.argv[1]}")
            sys.exit(1)
    
    generator = MockQueueGenerator(interval=interval)
    generator.run() 