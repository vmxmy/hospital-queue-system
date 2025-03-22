"""
使用Facebook Prophet算法预测等待时间的模块
"""
import pandas as pd
import numpy as np
from prophet import Prophet
from django.utils import timezone
import logging
from datetime import timedelta, datetime
import os
import pickle
from django.conf import settings

# 配置日志
logger = logging.getLogger(__name__)

class ProphetWaitTimePredictor:
    """使用Prophet算法预测等待时间的类"""
    
    def __init__(self, department_id=None, examination_id=None):
        """
        初始化预测器
        
        参数:
        - department_id: 科室ID，如果为None则为全局模型
        - examination_id: 检查项目ID，如果为None则为科室级模型
        """
        self.department_id = department_id
        self.examination_id = examination_id
        self.model = None
        self.model_file = self._get_model_path()
        self.load_model()
    
    def _get_model_path(self):
        """获取模型文件路径"""
        # 确保目录存在
        model_dir = os.path.join(settings.BASE_DIR, 'ml_models', 'prophet')
        os.makedirs(model_dir, exist_ok=True)
        
        # 根据科室和检查项目构建模型名称
        if self.examination_id:
            model_name = f"prophet_exam_{self.examination_id}.pkl"
        elif self.department_id:
            model_name = f"prophet_dept_{self.department_id}.pkl"
        else:
            model_name = "prophet_global.pkl"
            
        return os.path.join(model_dir, model_name)
    
    def load_model(self):
        """加载已训练的模型"""
        if os.path.exists(self.model_file):
            try:
                with open(self.model_file, 'rb') as f:
                    self.model = pickle.load(f)
                logger.info(f"已加载Prophet模型: {self.model_file}")
                return True
            except Exception as e:
                logger.error(f"加载Prophet模型失败: {str(e)}")
        return False
    
    def save_model(self):
        """保存训练好的模型"""
        if self.model:
            try:
                with open(self.model_file, 'wb') as f:
                    pickle.dump(self.model, f)
                logger.info(f"已保存Prophet模型: {self.model_file}")
                return True
            except Exception as e:
                logger.error(f"保存Prophet模型失败: {str(e)}")
        return False
    
    def prepare_training_data(self, historical_data):
        """
        准备训练数据
        
        参数:
        - historical_data: 包含历史等待时间数据的DataFrame或列表
          需要包含 'timestamp' 和 'wait_time' 两列
        
        返回:
        - 准备好的Prophet训练数据DataFrame (ds, y)
        """
        if isinstance(historical_data, list):
            df = pd.DataFrame(historical_data)
        else:
            df = historical_data.copy()
        
        # Prophet要求的列名为'ds'和'y'
        if 'timestamp' in df.columns:
            df['ds'] = pd.to_datetime(df['timestamp'])
        elif 'enter_time' in df.columns:
            df['ds'] = pd.to_datetime(df['enter_time'])
        elif 'created_at' in df.columns:
            df['ds'] = pd.to_datetime(df['created_at'])
        
        if 'wait_time' in df.columns:
            df['y'] = df['wait_time']
        elif 'actual_wait_time' in df.columns:
            df['y'] = df['actual_wait_time']
        elif 'estimated_wait_time' in df.columns:
            df['y'] = df['estimated_wait_time']
        
        # 确保数据中没有缺失值
        df = df[['ds', 'y']].dropna()
        
        # 确保数据按时间排序
        df = df.sort_values('ds')
        
        return df
    
    def train(self, historical_data, **kwargs):
        """
        训练Prophet模型
        
        参数:
        - historical_data: 历史等待时间数据，包含'timestamp'和'wait_time'列
        - **kwargs: 传递给Prophet模型的其他参数
        
        返回:
        - 训练是否成功
        """
        try:
            # 准备训练数据
            train_df = self.prepare_training_data(historical_data)
            
            if train_df.empty:
                logger.warning("训练数据为空，无法训练Prophet模型")
                return False
                
            # 确认有足够的非NaN行进行训练
            if len(train_df) < 2:
                logger.warning(f"训练数据点不足: {len(train_df)}行, Prophet模型至少需要2个数据点")
                return False
                
            # 记录数据情况便于调试
            logger.info(f"Prophet模型训练数据: {len(train_df)}行数据点")
            
            # 初始化和训练模型
            model = Prophet(
                # 默认参数，可通过kwargs覆盖
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05,
                seasonality_prior_scale=10.0,
                **kwargs
            )
            
            # 添加小时级别的季节性
            model.add_seasonality(
                name='hourly',
                period=24,
                fourier_order=5
            )
            
            # 确保数据类型正确
            train_df['ds'] = pd.to_datetime(train_df['ds'])
            train_df['y'] = train_df['y'].astype(float)
            
            # 拟合模型
            model.fit(train_df)
            
            # 保存模型
            self.model = model
            self.save_model()
            
            logger.info(f"成功训练Prophet模型: {self.model_file}")
            return True
            
        except Exception as e:
            logger.error(f"训练Prophet模型失败: {str(e)}")
            return False
    
    def predict(self, date=None, queue_count=None):
        """
        使用Prophet模型进行预测
        
        参数:
        - date: 预测日期时间，如果为None则使用当前时间
        - queue_count: 当前队列数量
        
        返回:
        - 预测的等待时间（分钟）
        """
        try:
            if not self.model:
                return None
            
            if date is None:
                date = timezone.now()
            
            # 移除时区信息
            date = date.replace(tzinfo=None)
            
            # 创建预测数据
            future_dates = pd.date_range(
                start=date,
                periods=1,
                freq='h'  # 使用小写的 'h' 替代大写的 'H'
            )
            
            future = pd.DataFrame({'ds': future_dates})
            
            # 添加额外特征
            if queue_count is not None:
                future['queue_count'] = queue_count
            
            # 添加其他特征
            future['hour'] = future['ds'].dt.hour
            future['day_of_week'] = future['ds'].dt.dayofweek
            
            # 进行预测
            forecast = self.model.predict(future)
            
            # 返回预测值（分钟）
            return max(1, round(forecast['yhat'].iloc[0]))
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Prophet预测失败: {str(e)}")
            return None
    
    def get_forecast_plot(self, periods=24, freq='H'):
        """
        生成预测图表
        
        参数:
        - periods: 预测未来几个时间单位
        - freq: 时间单位，默认为小时
        
        返回:
        - 图表对象
        """
        if not self.model:
            logger.warning("Prophet模型未加载，无法生成预测图表")
            return None
        
        try:
            # 创建未来数据点
            future = self.model.make_future_dataframe(periods=periods, freq=freq)
            
            # 预测
            forecast = self.model.predict(future)
            
            # 生成图表
            fig = self.model.plot(forecast)
            
            return fig
            
        except Exception as e:
            logger.error(f"生成Prophet预测图表失败: {str(e)}")
            return None


# 全局预测器实例
global_predictor = None

def get_prophet_predictor(department_id=None, examination_id=None):
    """
    获取Prophet预测器实例
    
    参数:
    - department_id: 科室ID，如果为None则为全局模型
    - examination_id: 检查项目ID，如果为None则为科室级模型
    
    返回:
    - ProphetWaitTimePredictor实例
    """
    global global_predictor
    
    # 如果请求全局预测器且已存在，直接返回
    if department_id is None and examination_id is None and global_predictor is not None:
        return global_predictor
    
    # 否则创建新的预测器
    predictor = ProphetWaitTimePredictor(department_id, examination_id)
    
    # 如果是全局预测器，保存为全局变量
    if department_id is None and examination_id is None:
        global_predictor = predictor
    
    return predictor 