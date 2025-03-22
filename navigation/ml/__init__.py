"""
机器学习模块，用于等待时间预测和排队优化
"""

import os
import logging

# 创建目录结构
os.makedirs('navigation/ml/trained_models', exist_ok=True)
os.makedirs('navigation/ml/data', exist_ok=True)

# 导入模型和服务
from .models import WaitTimePredictionService, WaitTimePredictor
from .data_collector import data_collector
from .trainer import model_trainer

# 创建全局预测服务实例
prediction_service = WaitTimePredictionService()

# 设置日志
logger = logging.getLogger(__name__)
logger.info("机器学习模块已初始化")

__all__ = ['prediction_service', 'data_collector', 'model_trainer'] 