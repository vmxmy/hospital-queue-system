"""
数据收集和预处理模块 - 用于收集和处理机器学习模型的训练数据
"""
import os
import csv
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from django.db.models import Count, Avg, Q, F, Sum, Max, Min
from django.utils import timezone
from django.conf import settings

from navigation.models import Queue, Department, Equipment, QueueHistory, Examination

# 配置日志 - 确保与tasks.py中的设置一致
logger = logging.getLogger(__name__)

# 确保此模块的日志也写入同一个文件
if not any(isinstance(h, logging.FileHandler) for h in logger.handlers):
    log_dir = os.path.join(settings.BASE_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_handler = logging.FileHandler(os.path.join(log_dir, 'ml_training.log'))
    formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s', '%Y-%m-%d %H:%M:%S')
    log_handler.setFormatter(formatter)
    logger.addHandler(log_handler)
    logger.setLevel(logging.DEBUG)

# 数据存储目录
DATA_DIR = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'data')
os.makedirs(DATA_DIR, exist_ok=True)


class WaitTimeDataCollector:
    """
    等待时间数据收集器 - 收集模型训练所需的数据
    """
    
    def __init__(self):
        self.data_file = os.path.join(DATA_DIR, 'wait_time_training_data.csv')
    
    def collect_historical_data(self, days=30, save=True):
        """
        收集历史队列等待时间数据作为训练数据
        
        参数:
            days (int): 向前收集多少天的数据
            save (bool): 是否保存到文件
            
        返回:
            DataFrame: 收集到的训练数据
        """
        start_date = timezone.now() - timedelta(days=days)
        
        # 收集已完成的队列记录
        completed_queues = Queue.objects.filter(
            status='completed',
            start_time__isnull=False,
            enter_time__isnull=False,
            actual_wait_time__isnull=False,
            created_at__gte=start_date
        ).select_related('department', 'equipment', 'examination')
        
        # 获取各科室容量数据
        departments = Department.objects.all()
        department_capacity = {}
        for dept in departments:
            # 科室容量 = 设备数量 + 医生数量
            equipment_count = Equipment.objects.filter(department_id=dept.id).count()
            # 假设医生数量字段存在，如果不存在，则假设每个科室有3-8名医生
            doctor_count = getattr(dept, 'doctor_count', np.random.randint(3, 9))
            department_capacity[dept.id] = equipment_count + doctor_count
        
        data = []
        for queue in completed_queues:
            try:
                # 获取该队列创建时科室的排队情况
                queue_time = queue.created_at
                dept_id = queue.department_id
                
                # 获取队列创建时的排队人数
                queue_count = Queue.objects.filter(
                    department_id=dept_id,
                    status='waiting',
                    created_at__lte=queue_time
                ).count()
                
                # 获取当时的设备状态
                equipment_available = Equipment.objects.filter(
                    department_id=dept_id,
                    status='available',
                    updated_at__lte=queue_time
                ).exists()
                equipment_status = 1 if equipment_available else 0
                
                # 提取时间特征
                timestamp = queue.enter_time
                hour = timestamp.hour
                day_of_week = timestamp.weekday()  # 0=周一, 6=周日
                is_weekend = 1 if day_of_week >= 5 else 0
                
                # 计算实际等待时间（分钟）
                actual_wait_time = queue.actual_wait_time or 0
                
                # 获取该科室的历史平均等待时间（过去7天）
                week_ago = queue_time - timedelta(days=7)
                historical_wait_times = Queue.objects.filter(
                    department_id=dept_id,
                    status='completed',
                    created_at__gte=week_ago,
                    created_at__lt=queue_time,
                    actual_wait_time__isnull=False
                ).values_list('actual_wait_time', flat=True)
                
                historical_wait_time = 0
                if historical_wait_times:
                    historical_wait_time = sum(historical_wait_times) / len(historical_wait_times)
                
                # 计算医生/设备工作效率
                # 效率 = 理想处理时间 / 实际处理时间
                # 如果存在处理时间字段，使用实际数据，否则基于设备状态估算
                staff_efficiency = 1.0  # 默认标准效率
                
                if hasattr(queue, 'processing_time') and queue.processing_time:
                    ideal_time = 15  # 假设理想处理时间为15分钟
                    actual_time = queue.processing_time
                    if actual_time > 0:
                        staff_efficiency = ideal_time / actual_time
                        # 将效率限制在合理范围内
                        staff_efficiency = max(0.5, min(1.5, staff_efficiency))
                else:
                    # 如果没有实际数据，根据设备状态估算效率
                    # 设备正常时效率较高，故障时效率较低
                    staff_efficiency = 1.2 if equipment_status == 1 else 0.7
                    # 添加随机扰动
                    staff_efficiency *= np.random.uniform(0.9, 1.1)
                
                # 构建特征向量
                data.append({
                    'queue_id': queue.id,
                    'department_id': dept_id,
                    'queue_count': queue_count,
                    'department_capacity': department_capacity.get(dept_id, 5),  # 默认容量为5
                    'staff_efficiency': staff_efficiency,
                    'equipment_status': equipment_status,
                    'historical_wait_time': historical_wait_time,
                    'hour': hour,
                    'day_of_week': day_of_week,
                    'is_weekend': is_weekend,
                    'priority': queue.priority,
                    'actual_wait_time': actual_wait_time,
                    'timestamp': timestamp
                })
            except Exception as e:
                logger.error(f"处理队列 {queue.id} 时出错: {str(e)}")
                continue
        
        # 转换为DataFrame
        df = pd.DataFrame(data)
        
        # 保存到CSV
        if save and not df.empty:
            try:
                df.to_csv(self.data_file, index=False)
                logger.info(f"已保存 {len(df)} 条训练数据到 {self.data_file}")
            except Exception as e:
                logger.error(f"保存数据失败: {str(e)}")
        
        return df
    
    def collect_real_time_data(self):
        """
        收集实时队列和设备状态数据
        
        返回:
            dict: 以科室ID为键的实时数据字典
        """
        from navigation.models import Department, Queue, Equipment
        
        # 收集每个科室的排队情况
        departments = Department.objects.all()
        real_time_data = {}
        
        # 获取各科室容量数据
        department_capacity = {}
        for dept in departments:
            equipment_count = Equipment.objects.filter(department_id=dept.id).count()
            doctor_count = getattr(dept, 'doctor_count', np.random.randint(3, 9))
            department_capacity[dept.id] = equipment_count + doctor_count
        
        for dept in departments:
            dept_id = dept.id
            
            # 统计等待中的队列数量
            queue_count = Queue.objects.filter(
                department_id=dept_id,
                status='waiting'
            ).count()
            
            # 检查设备状态
            equipment_status = 1  # 默认正常
            equipment = Equipment.objects.filter(department_id=dept_id).first()
            if equipment and equipment.status != 'available':
                equipment_status = 0  # 设备故障或维护中
            
            # 获取历史平均等待时间（过去24小时）
            day_ago = timezone.now() - timedelta(hours=24)
            historical_wait_times = Queue.objects.filter(
                department_id=dept_id,
                status='completed',
                created_at__gte=day_ago,
                actual_wait_time__isnull=False
            ).values_list('actual_wait_time', flat=True)
            
            historical_wait_time = 0
            if historical_wait_times:
                historical_wait_time = sum(historical_wait_times) / len(historical_wait_times)
            
            # 估算当前的医生/设备工作效率
            # 基于最近完成的队列计算效率
            staff_efficiency = 1.0  # 默认标准效率
            recent_queues = Queue.objects.filter(
                department_id=dept_id,
                status='completed',
                created_at__gte=day_ago
            ).order_by('-completed_at')[:5]
            
            if recent_queues.exists() and hasattr(recent_queues.first(), 'processing_time'):
                processing_times = [q.processing_time for q in recent_queues if q.processing_time]
                if processing_times:
                    avg_processing_time = sum(processing_times) / len(processing_times)
                    ideal_time = 15  # 假设理想处理时间
                    if avg_processing_time > 0:
                        staff_efficiency = ideal_time / avg_processing_time
                        staff_efficiency = max(0.5, min(1.5, staff_efficiency))
            
            real_time_data[dept_id] = {
                'queue_count': queue_count,
                'department_capacity': department_capacity.get(dept_id, 5),
                'equipment_status': equipment_status,
                'staff_efficiency': staff_efficiency,
                'historical_wait_time': historical_wait_time,
                'timestamp': timezone.now()
            }
        
        return real_time_data
    
    def get_training_data(self):
        """
        获取已保存的训练数据
        
        返回:
            DataFrame: 训练数据，如果文件不存在则返回None
        """
        try:
            if os.path.exists(self.data_file):
                return pd.read_csv(self.data_file)
            return None
        except Exception as e:
            logger.error(f"读取训练数据文件时出错: {str(e)}")
            return None


class QueueDataCollector:
    """收集队列历史数据的类"""
    
    def __init__(self, days_lookback=30):
        """
        初始化数据收集器
        
        参数:
        - days_lookback: 回溯多少天的数据
        """
        self.days_lookback = days_lookback
    
    def collect_historical_data(self, department_id=None, examination_id=None):
        """
        收集历史排队数据
        
        参数:
        - department_id: 科室ID，如果为None则收集所有科室
        - examination_id: 检查项目ID，如果为None则收集科室所有检查项目
        
        返回:
        - 包含历史数据的DataFrame
        """
        try:
            # 计算起始时间
            start_date = timezone.now() - timedelta(days=self.days_lookback)
            
            # 基础查询
            history_query = QueueHistory.objects.filter(
                created_at__gte=start_date,
                status__in=['completed', 'cancelled', 'skipped']  # 只考虑已完成、取消或跳过的队列
            )
            
            # 根据科室和检查项目筛选
            if department_id:
                history_query = history_query.filter(department_id=department_id)
            
            if examination_id:
                history_query = history_query.filter(examination_id=examination_id)
            
            # 获取数据
            queue_histories = history_query.values(
                'id', 'queue_id', 'patient_id', 'department_id', 'examination_id',
                'priority', 'status', 'enter_time', 'exit_time', 'created_at',
                'updated_at', 'estimated_wait_time', 'actual_wait_time'
            )
            
            if not queue_histories:
                logger.warning(f"未找到符合条件的历史数据：department_id={department_id}, examination_id={examination_id}")
                return pd.DataFrame()
            
            # 转换为DataFrame
            df = pd.DataFrame(list(queue_histories))
            
            # 计算实际等待时间（如果不存在）
            if 'actual_wait_time' not in df.columns or df['actual_wait_time'].isnull().all():
                df['enter_time'] = pd.to_datetime(df['enter_time'])
                df['exit_time'] = pd.to_datetime(df['exit_time'])
                
                # 计算等待时间（分钟）
                df['actual_wait_time'] = (df['exit_time'] - df['enter_time']).dt.total_seconds() / 60
                
                # 过滤掉不合理的值
                df = df[df['actual_wait_time'] >= 0]
            
            # 添加时间特征
            df['hour'] = pd.to_datetime(df['enter_time']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['enter_time']).dt.dayofweek
            df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
            
            logger.info(f"成功收集历史数据：{len(df)}条记录")
            return df
            
        except Exception as e:
            logger.error(f"收集历史数据失败：{str(e)}")
            return pd.DataFrame()
    
    def collect_current_queue_data(self, department_id=None, examination_id=None):
        """
        收集当前排队数据
        
        参数:
        - department_id: 科室ID，如果为None则收集所有科室
        - examination_id: 检查项目ID，如果为None则收集科室所有检查项目
        
        返回:
        - 包含当前队列数据的DataFrame
        """
        try:
            # 基础查询
            queue_query = Queue.objects.filter(
                status='waiting'  # 只考虑等待中的队列
            )
            
            # 根据科室和检查项目筛选
            if department_id:
                queue_query = queue_query.filter(department_id=department_id)
            
            if examination_id:
                queue_query = queue_query.filter(examination_id=examination_id)
            
            # 获取数据
            queues = queue_query.values(
                'id', 'patient_id', 'department_id', 'examination_id',
                'priority', 'status', 'enter_time', 'created_at',
                'updated_at', 'estimated_wait_time'
            )
            
            # 转换为DataFrame
            df = pd.DataFrame(list(queues))
            
            if df.empty:
                logger.info(f"当前没有等待中的队列：department_id={department_id}, examination_id={examination_id}")
                return df
            
            # 添加时间特征
            df['hour'] = pd.to_datetime(df['enter_time']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['enter_time']).dt.dayofweek
            df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
            
            logger.info(f"成功收集当前队列数据：{len(df)}条记录")
            return df
            
        except Exception as e:
            logger.error(f"收集当前队列数据失败：{str(e)}")
            return pd.DataFrame()
    
    def aggregate_by_time(self, df, time_unit='hour'):
        """
        按时间单位聚合数据
        
        参数:
        - df: 历史数据DataFrame
        - time_unit: 时间单位，可选值：'hour', 'day', 'week'
        
        返回:
        - 聚合后的DataFrame
        """
        if df.empty:
            return df
        
        # 确保时间列是datetime类型
        df['timestamp'] = pd.to_datetime(df['enter_time'])
        
        # 过滤无效的等待时间
        df = df.dropna(subset=['actual_wait_time'])
        df = df[df['actual_wait_time'] > 0]
        
        if len(df) < 2:
            logger.warning(f"过滤后数据点不足2个，无法聚合")
            return pd.DataFrame()
        
        # 根据时间单位设置重采样规则
        if time_unit == 'hour':
            resample_rule = 'h'
        elif time_unit == 'day':
            resample_rule = 'D'
        elif time_unit == 'week':
            resample_rule = 'W'
        else:
            resample_rule = 'h'  # 默认按小时
        
        # 设置索引并重采样
        df_indexed = df.set_index('timestamp')
        
        # 聚合数据 - 使用更健壮的聚合方法
        aggregated = df_indexed.resample(resample_rule).agg({
            'actual_wait_time': ['mean', 'count', 'min', 'max'],  # 多种聚合统计
            'id': 'count'  # 计数
        })
        
        # 展平多级索引
        aggregated.columns = ['_'.join(col).strip() for col in aggregated.columns.values]
        aggregated = aggregated.reset_index()
        
        # 确保有足够的非空数据点
        aggregated = aggregated[aggregated['actual_wait_time_count'] > 1]
        
        # 重命名列
        aggregated.rename(columns={
            'id_count': 'queue_count',
            'actual_wait_time_mean': 'wait_time'
        }, inplace=True)
        
        return aggregated
    
    def prepare_prophet_data(self, department_id=None, examination_id=None, time_unit='day'):
        """
        准备Prophet模型训练数据
        
        参数:
        - department_id: 科室ID
        - examination_id: 检查项目ID
        - time_unit: 时间单位，可选值：'hour', 'day', 'week'
        
        返回:
        - Prophet格式的训练数据
        """
        # 收集历史数据
        df = self.collect_historical_data(department_id, examination_id)
        
        if df.empty:
            logger.warning("没有可用的历史数据来准备Prophet模型")
            return pd.DataFrame()
        
        # 聚合数据
        aggregated = self.aggregate_by_time(df, time_unit)
        
        if aggregated.empty:
            logger.warning("聚合后没有足够的数据点来训练Prophet模型")
            return pd.DataFrame()
        
        # 转换为Prophet格式
        prophet_df = pd.DataFrame()
        prophet_df['ds'] = aggregated['timestamp'].dt.tz_localize(None)  # 移除时区信息
        prophet_df['y'] = aggregated['wait_time']
        
        # 添加额外特征
        if 'queue_count' in aggregated.columns:
            prophet_df['queue_count'] = aggregated['queue_count']
        
        if 'actual_wait_time_min' in aggregated.columns:
            prophet_df['wait_time_min'] = aggregated['actual_wait_time_min']
            
        if 'actual_wait_time_max' in aggregated.columns:
            prophet_df['wait_time_max'] = aggregated['actual_wait_time_max']
        
        if 'actual_wait_time_count' in aggregated.columns:
            prophet_df['wait_time_count'] = aggregated['actual_wait_time_count']
        
        # 再次确认有足够的非NaN行
        prophet_df = prophet_df.dropna(subset=['y'])
        
        if len(prophet_df) < 2:
            logger.warning("最终Prophet数据集中有效行数不足2行")
            return pd.DataFrame()
            
        logger.info(f"成功准备Prophet数据: {len(prophet_df)}行")
        return prophet_df


# 创建全局数据收集器实例
data_collector = WaitTimeDataCollector() 