"""
等待时间预测模型定义
"""
import os
import pickle
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from django.conf import settings
from django.core.cache import cache
import glob
from django.utils import timezone
import joblib
import json

# 导入XGBoost和Prophet
try:
    import xgboost as xgb
    from prophet import Prophet
    ADVANCED_MODELS_AVAILABLE = True
except ImportError:
    ADVANCED_MODELS_AVAILABLE = False
    logging.warning("XGBoost或Prophet库未安装，将使用基础模型")

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

# 模型存储路径
MODEL_DIR = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'trained_models')
os.makedirs(MODEL_DIR, exist_ok=True)


class WaitTimePredictor:
    """
    等待时间预测器 - 使用机器学习模型预测患者等待时间
    
    特征包括:
    - 科室ID
    - 当前排队人数
    - 科室容量 
    - 医生/设备工作效率
    - 设备状态(如设备故障)
    - 历史等待时间
    - 时间特征(小时、星期几、是否周末)
    """
    
    def __init__(self, department_id, model_type='xgboost'):
        self.department_id = department_id
        self.model_type = model_type
        
        # 扩展特征列表，包含新增的特征
        self.features = [
            'department_id', 'queue_count', 'department_capacity',
            'staff_efficiency', 'equipment_status', 'historical_wait_time',
            'hour', 'day_of_week', 'is_weekend'
        ]
        
        self.model = None
        
        # 根据模型类型选择对应的模型文件
        model_prefix = f'{model_type}_model' if model_type != 'default' else 'wait_time_model'
        self.model_file = os.path.join(MODEL_DIR, f'{model_prefix}_{department_id}.pkl')
        
        # 尝试加载主模型文件，如果失败则尝试其他可能的模型文件
        if not self.load_model():
            # 尝试加载其他可能的模型文件
            self.try_load_alternative_models()
        
    def try_load_alternative_models(self):
        """尝试加载其他可能的模型文件"""
        model_types = ['xgboost', 'prophet', 'random_forest', 'gradient_boosting', 'linear']
        
        for model_type in model_types:
            if model_type == self.model_type:
                continue  # 跳过已尝试的模型类型
                
            model_file = os.path.join(MODEL_DIR, f'{model_type}_model_{self.department_id}.pkl')
            if os.path.exists(model_file):
                try:
                    self.model = joblib.load(model_file)
                    self.model_type = model_type
                    self.model_file = model_file
                    logger.info(f"已加载科室 {self.department_id} 的备选 {model_type} 模型")
                    return True
                except Exception as e:
                    logger.error(f"加载备选模型 {model_file} 失败: {str(e)}")
        
        # 如果所有备选模型都加载失败，尝试旧版模型文件格式
        old_model_file = os.path.join(MODEL_DIR, f'wait_time_model_{self.department_id}.pkl')
        if os.path.exists(old_model_file):
            try:
                self.model = joblib.load(old_model_file)
                self.model_type = 'legacy'
                self.model_file = old_model_file
                logger.info(f"已加载科室 {self.department_id} 的旧版模型")
                return True
            except Exception as e:
                logger.error(f"加载旧版模型失败: {str(e)}")
                
        return False
        
    def load_model(self):
        """加载保存的模型"""
        if os.path.exists(self.model_file):
            try:
                logger.info(f"尝试加载模型文件: {self.model_file}")
                self.model = joblib.load(self.model_file)
                
                # 检查模型是否被正确加载
                if self.model is None:
                    logger.error(f"模型文件存在但加载后为None: {self.model_file}")
                    return False
                    
                # 验证模型对象
                if hasattr(self.model, 'predict'):
                    logger.info(f"已加载科室 {self.department_id} 的 {self.model_type} 等待时间预测模型")
                    return True
                else:
                    logger.error(f"加载的对象不是有效的模型（缺少predict方法）: {self.model_file}")
                    self.model = None
                    return False
                    
            except (ImportError, ModuleNotFoundError) as e:
                logger.error(f"加载模型时缺少必要的模块: {str(e)}")
                self.model = None
                return False
            except Exception as e:
                logger.error(f"加载模型失败: {str(e)}", exc_info=True)
                self.model = None
                return False
        else:
            logger.warning(f"模型文件不存在: {self.model_file}")
        return False
        
    def prepare_features(self, queue_count, equipment_status=1, priority=0, timestamp=None,
                        department_capacity=10, staff_efficiency=1.0, historical_wait_time=None):
        """
        准备模型输入特征
        
        参数:
        - queue_count (int): 当前排队人数
        - equipment_status (int): 设备状态 (1-正常, 0-故障)
        - priority (int): 优先级 (0-正常, 1-加急, 2-紧急)
        - timestamp (datetime): 预测时间点，如果为None则使用当前时间
        - department_capacity (int): 科室容量
        - staff_efficiency (float): 医生/设备工作效率
        - historical_wait_time (float): 历史平均等待时间
        
        返回:
        - features (dict): 模型输入特征
        """
        if timestamp is None:
            timestamp = timezone.now()
            
        # 提取时间特征
        hour = timestamp.hour
        day_of_week = timestamp.weekday()
        is_weekend = 1 if day_of_week >= 5 else 0
        
        # 如果没有提供历史等待时间，估算一个基于队列长度的值
        if historical_wait_time is None:
            historical_wait_time = queue_count * 12  # 假设平均每人12分钟
        
        # 构建特征字典
        X = {
            'department_id': self.department_id,
            'queue_count': queue_count,
            'department_capacity': department_capacity,
            'staff_efficiency': staff_efficiency,
            'equipment_status': equipment_status,
            'historical_wait_time': historical_wait_time,
            'hour': hour,
            'day_of_week': day_of_week,
            'is_weekend': is_weekend
        }
        
        # 对于Prophet模型，需要提供不同格式的特征
        if self.model_type == 'prophet':
            # Prophet需要ds列（日期时间）
            X = {'ds': timestamp}
        
        return X
        
    def predict(self, queue_count, equipment_status=1, priority=0, timestamp=None,
               department_capacity=10, staff_efficiency=1.0, historical_wait_time=None):
        """
        预测等待时间
        
        参数:
        - queue_count (int): 当前排队人数
        - equipment_status (int): 设备状态 (1-正常, 0-故障)
        - priority (int): 优先级 (0-正常, 1-加急, 2-紧急)
        - timestamp (datetime): 预测时间点，如果为None则使用当前时间
        - department_capacity (int): 科室容量
        - staff_efficiency (float): 医生/设备工作效率
        - historical_wait_time (float): 历史平均等待时间
        
        返回:
        - wait_time (float): 预计等待时间(分钟)
        """
        # 如果模型未加载，使用基于队列长度的简单计算
        if self.model is None:
            return self._fallback_prediction(queue_count, equipment_status, priority, 
                                           department_capacity, staff_efficiency)
            
        # 准备特征
        X = self.prepare_features(queue_count, equipment_status, priority, timestamp,
                                 department_capacity, staff_efficiency, historical_wait_time)
        
        try:
            # 根据模型类型进行预测
            if self.model_type == 'prophet':
                # Prophet模型需要特殊处理
                future = pd.DataFrame([X])
                forecast = self.model.predict(future)
                wait_time = forecast['yhat'].iloc[0]
            else:
                # 其他基于特征的模型
                X_df = pd.DataFrame([X])
                wait_time = self.model.predict(X_df)[0]
            
            # 根据优先级调整等待时间
            wait_time = wait_time * (0.9 ** priority)
            
            return max(0, wait_time)  # 确保等待时间非负
        except Exception as e:
            logger.error(f"预测等待时间时出错: {str(e)}")
            # 发生错误时回退到简单计算
            return self._fallback_prediction(queue_count, equipment_status, priority, 
                                          department_capacity, staff_efficiency)
    
    def _fallback_prediction(self, queue_count, equipment_status=1, priority=0, 
                           department_capacity=10, staff_efficiency=1.0):
        """
        当模型预测失败时的回退预测方法
        
        参数与predict方法相同
        
        返回:
        - wait_time (float): 预计等待时间(分钟)
        """
        # 基本处理时间（每人15分钟）
        base_processing_time = 15
        
        # 考虑科室容量和工作效率的影响
        capacity_factor = department_capacity / 10.0  # 标准化容量
        
        # 计算基本等待时间
        wait_time = queue_count * base_processing_time / (staff_efficiency * capacity_factor)
        
        # 设备故障时等待时间延长
        if equipment_status == 0:
            wait_time *= 1.5
            
        # 优先级每高一级，等待时间降低10%
        wait_time = wait_time * (0.9 ** priority)
        
        return max(0, wait_time)
            
    def save(self):
        """保存模型到文件"""
        if self.model is not None:
            try:
                joblib.dump(self.model, self.model_file)
                logger.info(f"已保存科室 {self.department_id} 的 {self.model_type} 等待时间预测模型")
                return True
            except Exception as e:
                logger.error(f"保存模型失败: {str(e)}")
        return False


class WaitTimePredictionService:
    """
    等待时间预测服务 - 管理科室的预测模型
    """
    
    def __init__(self):
        self.predictors = {}
        self.default_model_type = 'xgboost' if ADVANCED_MODELS_AVAILABLE else 'random_forest'
        self.load_all_models()
        
    def load_all_models(self):
        """加载所有保存的模型"""
        # 清空当前预测器字典
        self.predictors = {}
        
        # 查找所有保存的模型文件
        model_patterns = [
            'xgboost_model_*.pkl',
            'prophet_model_*.pkl',
            'random_forest_model_*.pkl',
            'gradient_boosting_model_*.pkl',
            'linear_model_*.pkl',
            'wait_time_model_*.pkl'  # 旧版格式
        ]
        
        # 优先加载高级模型
        loaded_departments = set()
        failed_departments = set()
        
        # 从数据库获取有效的科室ID
        valid_department_ids = set()
        try:
            from navigation.models import Department
            valid_department_ids = set(Department.objects.values_list('id', flat=True))
            logger.info(f"从数据库获取到 {len(valid_department_ids)} 个科室: {sorted(list(valid_department_ids))}")
        except Exception as e:
            logger.error(f"获取科室列表时出错: {str(e)}")
        
        # 获取所有可用的模型文件
        all_model_files = []
        for pattern in model_patterns:
            model_files = glob.glob(os.path.join(MODEL_DIR, pattern))
            model_type = pattern.split('_')[0]
            for model_file in model_files:
                all_model_files.append((model_file, model_type))
        
        logger.info(f"找到 {len(all_model_files)} 个模型文件")
        
        # 按照文件名中的部门ID排序，确保顺序加载
        all_model_files.sort(key=lambda x: int(os.path.basename(x[0]).split('_')[-1].replace('.pkl', '')))
        
        for model_file, model_type in all_model_files:
            try:
                # 从文件名提取部门ID
                filename = os.path.basename(model_file)
                parts = filename.split('_')
                
                # 提取ID部分（最后一部分，去掉.pkl）
                if 'wait_time_model_' in filename:
                    dept_id = int(filename.replace('wait_time_model_', '').replace('.pkl', ''))
                else:
                    dept_id = int(parts[-1].replace('.pkl', ''))
                
                # 检查科室ID是否存在于数据库中
                if valid_department_ids and dept_id not in valid_department_ids:
                    logger.warning(f"科室ID {dept_id} 在数据库中不存在，跳过加载对应模型: {model_file}")
                    continue
                
                # 如果该科室已加载过模型，跳过（保证先加载的高级模型优先级更高）
                if dept_id in loaded_departments:
                    logger.info(f"科室 {dept_id} 已有模型加载，跳过 {model_file}")
                    continue
                    
                # 如果该科室已尝试加载但失败，也跳过
                if dept_id in failed_departments:
                    logger.info(f"科室 {dept_id} 模型之前加载失败，跳过 {model_file}")
                    continue
                
                logger.info(f"正在加载科室 {dept_id} 的 {model_type} 模型: {model_file}")
                
                # 创建并加载预测器
                predictor = WaitTimePredictor(dept_id, model_type)
                if predictor.model is not None:
                    self.predictors[dept_id] = predictor
                    loaded_departments.add(dept_id)
                    logger.info(f"已加载科室 {dept_id} 的 {model_type} 等待时间预测模型")
                else:
                    failed_departments.add(dept_id)
                    logger.error(f"科室 {dept_id} 的 {model_type} 模型加载失败，模型对象为None")
                
            except Exception as e:
                if 'dept_id' in locals():
                    failed_departments.add(dept_id)
                logger.error(f"加载模型 {model_file} 时出错: {str(e)}", exc_info=True)
        
        total_departments = len(loaded_departments) + len(failed_departments)
        logger.info(f"共尝试加载 {total_departments} 个科室模型，成功 {len(loaded_departments)} 个，失败 {len(failed_departments)} 个")
        if failed_departments:
            logger.warning(f"以下科室的模型加载失败: {sorted(list(failed_departments))}")
        
        return len(loaded_departments) > 0
    
    def is_ready(self):
        """检查是否有可用的预测模型"""
        return len(self.predictors) > 0
    
    def get_available_departments(self):
        """获取已有预测模型的科室ID列表"""
        return list(self.predictors.keys())
    
    def get_performance_metrics(self):
        """获取模型性能指标"""
        # 从数据库获取全部科室
        from navigation.models import Department
        all_departments = {d.id: d.name for d in Department.objects.all()}
        
        # 创建动态的性能指标列表
        metrics = []
        
        # 获取模型性能指标文件
        metrics_file = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'model_metrics.json')
        metrics_data = {}
        
        # 尝试从文件加载已存储的性能指标
        if os.path.exists(metrics_file):
            try:
                with open(metrics_file, 'r') as f:
                    metrics_data = json.load(f)
                logger.info(f"已从文件加载 {len(metrics_data)} 个模型的性能指标")
            except Exception as e:
                logger.error(f"加载模型性能指标文件时出错: {str(e)}")
        
        # 检查模型文件来确定所有可能的科室模型
        model_files = glob.glob(os.path.join(MODEL_DIR, '*_model_*.pkl'))
        available_dept_ids = set()
        
        for model_file in model_files:
            try:
                # 提取科室ID
                filename = os.path.basename(model_file)
                dept_id = int(filename.split('_')[-1].replace('.pkl', ''))
                available_dept_ids.add(dept_id)
            except Exception:
                continue
        
        # 为每个科室创建性能指标
        for dept_id in sorted(available_dept_ids):
            dept_name = all_departments.get(dept_id, f'科室 {dept_id}')
            
            # 确定模型类型
            if dept_id in self.predictors:
                model_type = self.predictors[dept_id].model_type
            else:
                # 检查哪种类型的模型文件存在
                for model_type in ['xgboost', 'prophet', 'random_forest', 'gradient_boosting', 'linear']:
                    if os.path.exists(os.path.join(MODEL_DIR, f'{model_type}_model_{dept_id}.pkl')):
                        break
                else:
                    model_type = '未知'
            
            # 获取性能指标，默认使用样例值，如果有存储的数据则使用存储的
            dept_metrics = metrics_data.get(str(dept_id), {})
            
            # 构建指标
            metric = {
                'department_id': dept_id,
                'department__name': dept_name,
                'model_type': model_type if dept_id in self.predictors else f'未加载 ({model_type})',
                'mae': dept_metrics.get('mae', 0.0),
                'accuracy': dept_metrics.get('accuracy', 0.0),
                'r2_score': dept_metrics.get('r2', 0.0),
                'sample_count': dept_metrics.get('sample_count', 0)
            }
            
            metrics.append(metric)
            
        # 如果没有找到任何模型，显示示例数据
        if not metrics:
            metrics = [
                {
                    'department__name': '心电图科',
                    'model_type': self.predictors.get(1, WaitTimePredictor(1)).model_type if 1 in self.predictors else '无模型',
                    'mae': 5.2,
                    'accuracy': 85.7,
                    'r2_score': 0.823,
                    'sample_count': 1245
                },
                {
                    'department__name': '超声科',
                    'model_type': self.predictors.get(2, WaitTimePredictor(2)).model_type if 2 in self.predictors else '无模型',
                    'mae': 7.8,
                    'accuracy': 82.1,
                    'r2_score': 0.756,
                    'sample_count': 968
                },
                {
                    'department__name': '放射科',
                    'model_type': self.predictors.get(3, WaitTimePredictor(3)).model_type if 3 in self.predictors else '无模型',
                    'mae': 12.5,
                    'accuracy': 76.3,
                    'r2_score': 0.681,
                    'sample_count': 1532
                }
            ]
        
        return metrics
    
    def predict_wait_time(self, department_id, queue_count, equipment_status=1, priority=0,
                         department_capacity=None, staff_efficiency=None, historical_wait_time=None):
        """
        预测特定科室、特定条件下的等待时间
        
        参数:
        - department_id: 科室ID
        - queue_count: 队列中排在前面的人数
        - equipment_status: 设备状态 (1-正常, 0-故障)
        - priority: 优先级 (0-正常, 1-加急, 2-紧急)
        - department_capacity: 科室容量
        - staff_efficiency: 医生/设备工作效率
        - historical_wait_time: 历史平均等待时间
        
        返回:
        - 预计等待时间(分钟)
        """
        # 获取其他特征数据
        if department_capacity is None or staff_efficiency is None or historical_wait_time is None:
            # 尝试从数据收集器获取实时数据
            try:
                from .data_collector import data_collector
                real_time_data = data_collector.collect_real_time_data()
                dept_data = real_time_data.get(department_id, {})
                
                # 设置默认值
                if department_capacity is None:
                    department_capacity = dept_data.get('department_capacity', 10)
                if staff_efficiency is None:
                    staff_efficiency = dept_data.get('staff_efficiency', 1.0)
                if historical_wait_time is None:
                    historical_wait_time = dept_data.get('historical_wait_time', queue_count * 12)
            except Exception as e:
                logger.error(f"获取实时数据失败: {str(e)}")
                # 设置默认值
                if department_capacity is None:
                    department_capacity = 10
                if staff_efficiency is None:
                    staff_efficiency = 1.0
                if historical_wait_time is None:
                    historical_wait_time = queue_count * 12
        
        # 如果有该科室的预测模型，使用模型预测
        if department_id in self.predictors:
            predictor = self.predictors[department_id]
            return predictor.predict(queue_count, equipment_status, priority, None,
                                   department_capacity, staff_efficiency, historical_wait_time)
        
        # 否则使用简单的回退计算
        return self._simple_prediction(queue_count, equipment_status, priority, 
                                      department_capacity, staff_efficiency)
    
    def _simple_prediction(self, queue_count, equipment_status=1, priority=0, 
                          department_capacity=10, staff_efficiency=1.0):
        """简单的等待时间预测方法，不使用机器学习模型"""
        # 基本处理时间（每人15分钟）
        base_processing_time = 15
        
        # 考虑科室容量和工作效率的影响
        capacity_factor = department_capacity / 10.0  # 标准化容量
        
        # 计算基本等待时间
        wait_time = queue_count * base_processing_time / (staff_efficiency * capacity_factor)
        
        # 设备故障时等待时间延长
        if equipment_status == 0:
            wait_time *= 1.5
            
        # 优先级每高一级，等待时间降低10%
        wait_time = wait_time * (0.9 ** priority)
        
        return max(0, wait_time)
        
    def train_all_models(self):
        """
        训练所有科室的模型
        """
        try:
            from .trainer import model_trainer
            logger.info("开始调用model_trainer.train_all_models()方法")
            try:
                # 先清理无效模型
                logger.info("清理数据库中不存在科室的模型文件")
                self.cleanup_invalid_models()
                
                # 训练模型
                success = model_trainer.train_all_models()
                if success:
                    # 重新加载训练好的模型
                    logger.info("模型训练成功，正在重新加载模型")
                    self.load_all_models()
                else:
                    logger.error("模型训练返回失败状态")
                return success
            except Exception as e:
                logger.error(f"调用model_trainer.train_all_models()时发生异常: {str(e)}", exc_info=True)
                return False
        except ImportError as e:
            logger.error(f"导入model_trainer模块失败: {str(e)}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"训练模型时发生未知错误: {str(e)}", exc_info=True)
            return False

    def cleanup_invalid_models(self):
        """清理数据库中不存在科室的模型文件"""
        # 从数据库获取有效的科室ID
        valid_department_ids = set()
        try:
            from navigation.models import Department
            valid_department_ids = set(Department.objects.values_list('id', flat=True))
            logger.info(f"从数据库获取到 {len(valid_department_ids)} 个科室: {sorted(list(valid_department_ids))}")
        except Exception as e:
            logger.error(f"获取科室列表时出错: {str(e)}")
            return False
            
        if not valid_department_ids:
            logger.warning("未找到有效的科室ID，取消清理")
            return False
        
        # 查找所有模型文件
        model_files = glob.glob(os.path.join(MODEL_DIR, '*_model_*.pkl'))
        invalid_files = []
        
        for model_file in model_files:
            try:
                # 从文件名提取部门ID
                filename = os.path.basename(model_file)
                if '_model_' in filename:
                    dept_id = int(filename.split('_')[-1].replace('.pkl', ''))
                    if dept_id not in valid_department_ids:
                        invalid_files.append(model_file)
            except Exception as e:
                logger.error(f"解析模型文件名时出错: {str(e)}")
                
        # 清理无效文件
        for file_path in invalid_files:
            try:
                # 将文件移动到备份目录而不是直接删除
                backup_dir = os.path.join(MODEL_DIR, 'backup')
                os.makedirs(backup_dir, exist_ok=True)
                
                # 获取文件名
                filename = os.path.basename(file_path)
                backup_path = os.path.join(backup_dir, filename)
                
                # 移动文件
                import shutil
                shutil.move(file_path, backup_path)
                logger.info(f"已将无效科室的模型文件移动到备份目录: {file_path} -> {backup_path}")
            except Exception as e:
                logger.error(f"清理模型文件时出错: {str(e)}")
                
        logger.info(f"共清理了 {len(invalid_files)} 个无效科室的模型文件")
        return len(invalid_files) > 0


# 创建全局预测服务实例
prediction_service = WaitTimePredictionService() 