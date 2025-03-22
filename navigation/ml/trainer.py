"""
用于训练和评估机器学习模型的脚本
"""
import os
import logging
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端，避免在非主线程创建窗口
import matplotlib.pyplot as plt
import joblib
from django.conf import settings
from django.db.models import Count
from navigation.models import Department

# 导入新增的库
import xgboost as xgb
from prophet import Prophet

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

class ModelTrainer:
    """
    机器学习模型训练和评估类
    """
    
    def __init__(self):
        """
        初始化训练器
        """
        self.model_dir = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'trained_models')
        os.makedirs(self.model_dir, exist_ok=True)
        
        # 初始化与其他模块的连接
        from .data_collector import data_collector
        self.data_collector = data_collector
        from .models import prediction_service
        self.prediction_service = prediction_service
    
    def prepare_features(self, df):
        """
        准备特征和目标变量
        
        Args:
            df: 输入的DataFrame
            
        Returns:
            特征矩阵X和目标变量y
        """
        # 新的特征列 - 按照需求调整特征
        feature_columns = [
            'department_id',          # 科室ID
            'queue_count',            # 当前排队人数
            'department_capacity',    # 科室容量
            'staff_efficiency',       # 医生/设备工作效率
            'equipment_status',       # 设备状态(突发事件如设备故障)
            'historical_wait_time',   # 历史等待时间
            'hour', 'day_of_week', 'is_weekend'  # 时间相关特征
        ]
        
        # 检查所需特征是否存在，不存在则添加模拟数据
        existing_columns = df.columns.tolist()
        for col in feature_columns:
            if col not in existing_columns:
                if col == 'department_capacity':
                    # 根据科室ID生成容量数据
                    df['department_capacity'] = df['department_id'].apply(
                        lambda x: np.random.randint(5, 15)
                    )
                    logger.warning(f"添加模拟数据列: {col}")
                    
                elif col == 'staff_efficiency':
                    # 生成0.5-1.5之间的效率值(1为标准效率)
                    df['staff_efficiency'] = np.random.uniform(0.5, 1.5, size=len(df))
                    logger.warning(f"添加模拟数据列: {col}")
                    
                elif col == 'historical_wait_time':
                    # 基于队列长度生成历史等待时间
                    df['historical_wait_time'] = df['queue_count'] * 12 + np.random.normal(0, 5, size=len(df))
                    df['historical_wait_time'] = df['historical_wait_time'].apply(lambda x: max(0, x))
                    logger.warning(f"添加模拟数据列: {col}")
                else:
                    logger.error(f"训练数据中缺少特征: {col}，且无法自动生成")
                    raise ValueError(f"训练数据中缺少特征: {col}")
        
        # 目标变量
        target_column = 'actual_wait_time'
        if target_column not in df.columns:
            logger.error(f"训练数据中缺少目标变量: {target_column}")
            raise ValueError(f"训练数据中缺少目标变量: {target_column}")
        
        # 准备特征和目标
        X = df[feature_columns]
        y = df[target_column]
        
        return X, y
    
    def prepare_time_series_data(self, df, department_id=None):
        """
        为Prophet准备时间序列数据
        
        Args:
            df: 输入的DataFrame
            department_id: 科室ID，用于过滤数据
            
        Returns:
            适合Prophet的DataFrame
        """
        if department_id is not None:
            df = df[df['department_id'] == department_id]
        
        # 确保有时间列，如果没有则创建
        if 'timestamp' not in df.columns:
            # 生成模拟时间戳
            current_time = pd.Timestamp.now().floor('D')
            timestamps = []
            
            for _ in range(len(df)):
                # 生成随机的过去时间
                random_hours = np.random.randint(-30*24, 0)  # 过去30天内
                timestamps.append(current_time + pd.Timedelta(hours=random_hours))
            
            df['timestamp'] = timestamps
            df = df.sort_values('timestamp')
        
        # 准备Prophet需要的格式: ds(日期)和y(目标值)
        prophet_df = df[['timestamp', 'actual_wait_time']].rename(
            columns={'timestamp': 'ds', 'actual_wait_time': 'y'}
        )
        
        return prophet_df
    
    def train_model(self, df, department_id=None, model_type='xgboost'):
        """
        训练机器学习模型
        
        Args:
            df: 包含训练数据的DataFrame
            department_id: 科室ID，用于过滤和保存模型
            model_type: 模型类型，可选 'xgboost', 'prophet', 'random_forest', 'gradient_boosting', 'linear'
            
        Returns:
            训练好的模型和评估结果
        """
        try:
            # 如果指定了科室ID，只训练该科室的数据
            if department_id is not None:
                df = df[df['department_id'] == department_id]
                if len(df) < 20:
                    logger.warning(f"科室 {department_id} 的训练数据不足，仅有 {len(df)} 条记录")
                    return None, None
            
            logger.info(f"使用 {len(df)} 条记录训练模型，模型类型: {model_type}")
            
            # 打印数据前几行以便调试
            try:
                logger.debug(f"训练数据前5行:\n{df.head(5).to_string()}")
                logger.debug(f"训练数据列: {df.columns.tolist()}")
            except Exception as e:
                logger.error(f"打印调试信息时出错: {str(e)}")
            
            # 根据模型类型选择不同的处理方式
            if model_type == 'prophet':
                return self._train_prophet_model(df, department_id)
            else:
                # 其他基于特征的模型
                return self._train_feature_based_model(df, department_id, model_type)
            
        except Exception as e:
            logger.error(f"训练模型过程中发生未捕获的异常: {str(e)}", exc_info=True)
            return None, None
    
    def _train_prophet_model(self, df, department_id=None):
        """
        训练Prophet时间序列模型
        
        Args:
            df: 输入数据
            department_id: 科室ID，用于保存模型
            
        Returns:
            训练好的模型和评估指标
        """
        try:
            # 准备Prophet格式的数据
            prophet_df = self.prepare_time_series_data(df, department_id)
            logger.info(f"准备Prophet数据完成，数据形状: {prophet_df.shape}")
            
            # 分割训练集和测试集
            train_size = int(len(prophet_df) * 0.8)
            train_df = prophet_df.iloc[:train_size]
            test_df = prophet_df.iloc[train_size:]
            
            if len(train_df) < 10:
                logger.warning(f"Prophet训练数据不足，仅有 {len(train_df)} 条记录")
                return None, None
            
            # 创建并训练Prophet模型
            model = Prophet(
                seasonality_mode='multiplicative',
                daily_seasonality=True,
                weekly_seasonality=True,
                changepoint_prior_scale=0.05
            )
            model.fit(train_df)
            logger.info("Prophet模型训练完成")
            
            # 在测试集上进行预测
            future = model.make_future_dataframe(periods=len(test_df))
            forecast = model.predict(future)
            
            # 评估模型
            predictions = forecast.iloc[-len(test_df):]['yhat'].values
            actual = test_df['y'].values
            
            metrics = {
                'mae': mean_absolute_error(actual, predictions),
                'rmse': np.sqrt(mean_squared_error(actual, predictions)),
                'r2': r2_score(actual, predictions)
            }
            logger.info(f"Prophet模型评估指标: MAE={metrics['mae']:.2f}, RMSE={metrics['rmse']:.2f}, R²={metrics['r2']:.2f}")
            
            # 如果指定了科室ID，保存模型
            if department_id is not None:
                model_path = os.path.join(self.model_dir, f'prophet_model_{department_id}.pkl')
                with open(model_path, 'wb') as f:
                    joblib.dump(model, f)
                logger.info(f"Prophet模型已保存到: {model_path}")
            
            return model, metrics
        
        except Exception as e:
            logger.error(f"训练Prophet模型时出错: {str(e)}", exc_info=True)
            return None, None
    
    def _train_feature_based_model(self, df, department_id=None, model_type='xgboost'):
        """
        训练基于特征的模型(XGBoost, RandomForest等)
        
        Args:
            df: 训练数据
            department_id: 科室ID，用于保存模型
            model_type: 模型类型
            
        Returns:
            训练好的模型和评估指标
        """
        try:
            # 准备特征和目标
            X, y = self.prepare_features(df)
            logger.info(f"成功准备特征 X 形状: {X.shape} 和目标 y 形状: {y.shape}")
            
            # 分割训练集和测试集
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            logger.info(f"数据集分割完成: 训练集大小 {X_train.shape[0]}, 测试集大小 {X_test.shape[0]}")
            
            # 根据选择的模型类型创建模型
            if model_type == 'xgboost':
                model = xgb.XGBRegressor(
                    n_estimators=100,
                    learning_rate=0.1,
                    max_depth=5,
                    subsample=0.8,
                    colsample_bytree=0.8,
                    random_state=42,
                    n_jobs=-1
                )
                logger.info("使用XGBoost模型")
            elif model_type == 'random_forest':
                model = RandomForestRegressor(
                    n_estimators=50,
                    max_depth=10,
                    min_samples_split=2,
                    min_samples_leaf=1,
                    random_state=42,
                    n_jobs=-1
                )
                logger.info("使用RandomForest模型")
            elif model_type == 'gradient_boosting':
                model = GradientBoostingRegressor(
                    n_estimators=50,
                    learning_rate=0.1,
                    max_depth=3,
                    random_state=42
                )
                logger.info("使用GradientBoosting模型")
            elif model_type == 'linear':
                model = LinearRegression()
                logger.info("使用Linear模型")
            else:
                raise ValueError(f"不支持的模型类型: {model_type}")
            
            # 训练模型
            logger.info("开始训练模型...")
            model.fit(X_train, y_train)
            logger.info("模型训练完成")
            
            # 评估模型
            y_pred = model.predict(X_test)
            metrics = {
                'mae': mean_absolute_error(y_test, y_pred),
                'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
                'r2': r2_score(y_test, y_pred)
            }
            logger.info(f"模型评估指标: MAE={metrics['mae']:.2f}, RMSE={metrics['rmse']:.2f}, R²={metrics['r2']:.2f}")
            
            # 特征重要性（如果模型支持）
            try:
                if hasattr(model, 'feature_importances_'):
                    # 创建特征重要性的DataFrame
                    importance_df = pd.DataFrame({
                        'feature': X.columns,
                        'importance': model.feature_importances_
                    }).sort_values('importance', ascending=False)
                    
                    logger.info(f"特征重要性:\n{importance_df.to_string()}")
                    metrics['feature_importance'] = importance_df
            except Exception as e:
                logger.error(f"计算特征重要性时出错: {str(e)}")
            
            # 如果指定了科室ID，保存模型
            if department_id is not None:
                model_path = os.path.join(self.model_dir, f'{model_type}_model_{department_id}.pkl')
                joblib.dump(model, model_path)
                logger.info(f"模型已保存到: {model_path}")
            
            return model, metrics
            
        except Exception as e:
            logger.error(f"训练特征模型时出错: {str(e)}", exc_info=True)
            return None, None
    
    def hyper_parameter_tuning(self, df, department_id=None, model_type='xgboost'):
        """
        对模型进行超参数调优
        
        Args:
            df: 训练数据
            department_id: 科室ID用于过滤数据
            model_type: 模型类型
            
        Returns:
            最佳模型和评估结果
        """
        # 如果指定了科室ID，只训练该科室的数据
        if department_id is not None:
            df = df[df['department_id'] == department_id]
            if len(df) < 50:
                logger.warning(f"科室 {department_id} 的训练数据不足，仅有 {len(df)} 条记录，跳过超参数调优")
                return self.train_model(df, department_id, model_type)
        
        # 准备特征和目标
        X, y = self.prepare_features(df)
        
        # 分割训练集和测试集
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        
        # 根据模型类型设置参数网格
        if model_type == 'xgboost':
            base_model = xgb.XGBRegressor(random_state=42, n_jobs=-1)
            param_grid = {
                'n_estimators': [50, 100, 200],
                'learning_rate': [0.01, 0.05, 0.1],
                'max_depth': [3, 5, 7],
                'subsample': [0.6, 0.8, 1.0],
                'colsample_bytree': [0.6, 0.8, 1.0]
            }
        elif model_type == 'random_forest':
            base_model = RandomForestRegressor(random_state=42, n_jobs=-1)
            param_grid = {
                'n_estimators': [50, 100, 200],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4]
            }
        else:
            logger.warning(f"模型类型 {model_type} 不支持超参数调优，使用默认参数")
            return self.train_model(df, department_id, model_type)
        
        # 使用网格搜索进行超参数调优
        grid_search = GridSearchCV(
            estimator=base_model,
            param_grid=param_grid,
            cv=5,
            scoring='neg_mean_absolute_error',
            verbose=1,
            n_jobs=-1
        )
        
        # 训练网格搜索模型
        grid_search.fit(X_train, y_train)
        
        # 获取最佳模型
        best_model = grid_search.best_estimator_
        
        # 评估最佳模型
        y_pred = best_model.predict(X_test)
        metrics = {
            'mae': mean_absolute_error(y_test, y_pred),
            'rmse': np.sqrt(mean_squared_error(y_test, y_pred)),
            'r2': r2_score(y_test, y_pred),
            'best_params': grid_search.best_params_
        }
        
        logger.info(f"超参数调优完成，最佳参数: {grid_search.best_params_}")
        
        # 特征重要性
        importance_df = pd.DataFrame({
            'feature': X.columns,
            'importance': best_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info(f"特征重要性:\n{importance_df.to_string()}")
        metrics['feature_importance'] = importance_df
        
        # 如果指定了科室ID，保存模型
        if department_id is not None:
            model_path = os.path.join(self.model_dir, f'{model_type}_tuned_model_{department_id}.pkl')
            joblib.dump(best_model, model_path)
            logger.info(f"最佳模型已保存到: {model_path}")
        
        return best_model, metrics
    
    def train_all_department_models(self, df):
        """
        为所有科室训练单独的模型
        
        Args:
            df: 训练数据
            
        Returns:
            科室ID到模型和评估结果的映射
        """
        # 获取所有唯一的科室ID
        department_ids = df['department_id'].unique()
        
        # 存储训练结果
        results = {}
        
        # 为每个科室训练模型
        for dept_id in department_ids:
            logger.info(f"为科室 {dept_id} 训练模型")
            
            # 训练模型
            model, metrics = self.train_model(df, department_id=dept_id)
            
            # 如果训练成功，存储结果
            if model is not None:
                results[dept_id] = {
                    'model': model,
                    'metrics': metrics
                }
        
        return results
    
    def generate_evaluation_plots(self, model, X_test, y_test, department_id=None):
        """
        生成模型评估图表
        
        Args:
            model: 已训练的模型
            X_test: 测试特征
            y_test: 测试目标
            department_id: 科室ID用于文件命名
        """
        # 确保存在图表目录
        plots_dir = os.path.join(self.model_dir, 'plots')
        os.makedirs(plots_dir, exist_ok=True)
        
        # 预测值
        y_pred = model.predict(X_test)
        
        # 1. 预测值与实际值的对比散点图
        plt.figure(figsize=(10, 6))
        plt.scatter(y_test, y_pred, alpha=0.5)
        plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')
        plt.xlabel('实际等待时间 (分钟)')
        plt.ylabel('预测等待时间 (分钟)')
        plt.title(f'科室 {department_id} 等待时间预测模型评估')
        plt.grid(True)
        
        # 保存图表
        file_name = f'prediction_vs_actual_dept_{department_id}.png' if department_id else 'prediction_vs_actual.png'
        plt.savefig(os.path.join(plots_dir, file_name))
        plt.close()
        
        # 2. 如果模型有特征重要性，绘制特征重要性图
        if hasattr(model, 'feature_importances_'):
            # 特征重要性
            feature_importance = pd.DataFrame({
                'feature': X_test.columns,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            plt.figure(figsize=(10, 8))
            plt.barh(feature_importance['feature'], feature_importance['importance'])
            plt.xlabel('重要性')
            plt.ylabel('特征')
            plt.title(f'科室 {department_id} 特征重要性')
            plt.tight_layout()
            
            # 保存图表
            file_name = f'feature_importance_dept_{department_id}.png' if department_id else 'feature_importance.png'
            plt.savefig(os.path.join(plots_dir, file_name))
            plt.close()
        
        logger.info(f"已生成科室 {department_id} 的评估图表")

    def train_all_models(self, df=None, algorithm='xgboost'):
        """
        训练所有科室的等待时间预测模型
        
        Args:
            df: 训练数据，如果为None则从数据收集器获取
            algorithm: 使用的算法，可选值: 'xgboost', 'prophet', 'random_forest', 'gradient_boosting', 'linear'
            
        Returns:
            bool: 训练是否成功
        """
        try:
            logger.info(f"开始训练所有科室的等待时间预测模型，使用算法: {algorithm}")
            
            # 获取训练数据
            if df is None:
                try:
                    # 尝试从数据收集器获取数据
                    if not hasattr(self, 'data_collector') or self.data_collector is None:
                        from navigation.ml.data_collector import data_collector
                        self.data_collector = data_collector
                        
                    df = self.data_collector.get_training_data()
                    logger.info(f"从数据收集器获取到 {len(df)} 条训练数据")
                except Exception as e:
                    logger.error(f"获取训练数据失败: {str(e)}")
                    logger.info("将使用模拟训练数据")
                    df = self._generate_simulated_training_data()
            
            # 检查是否有足够的训练数据
            if df is None or len(df) < 50:
                logger.warning(f"训练数据不足，仅有 {0 if df is None else len(df)} 条记录")
                logger.info("生成模拟训练数据")
                df = self._generate_simulated_training_data()
            
            # 获取所有科室列表
            departments = list(Department.objects.all())
            
            # 记录数据库中的科室ID
            valid_dept_ids = {dept.id for dept in departments}
            logger.info(f"数据库中的科室ID: {sorted(list(valid_dept_ids))}")
            
            if not departments:
                departments = self._get_default_departments()
            
            # 过滤训练数据，只保留数据库中存在的科室的数据
            if 'department_id' in df.columns:
                original_count = len(df)
                df = df[df['department_id'].isin(valid_dept_ids)]
                filtered_count = len(df)
                if filtered_count < original_count:
                    logger.warning(f"过滤掉了 {original_count - filtered_count} 条不存在科室的数据，剩余 {filtered_count} 条数据")
            
            # 为每个科室训练模型
            successful_count = 0
            for dept in departments:
                try:
                    logger.info(f"开始训练科室 {dept.id}:{dept.name} 的等待时间预测模型，使用算法: {algorithm}")
                    success = self._train_and_save_model(dept.id, df, algorithm=algorithm)
                    if success:
                        successful_count += 1
                        logger.info(f"科室 {dept.id}:{dept.name} 的等待时间预测模型训练成功")
                    else:
                        logger.error(f"科室 {dept.id}:{dept.name} 的等待时间预测模型训练失败")
                except Exception as e:
                    logger.error(f"训练科室 {dept.id}:{dept.name} 模型时出错: {str(e)}")
            
            # 记录训练结果
            logger.info(f"模型训练完成，共有 {successful_count}/{len(departments)} 个科室模型训练成功")
            
            # 确保重新加载所有模型
            try:
                from navigation.ml.models import prediction_service
                logger.info("训练完成，正在强制重新加载所有模型...")
                prediction_service.load_all_models()
                loaded_models = len(prediction_service.get_available_departments())
                logger.info(f"重新加载完成，共加载了 {loaded_models} 个模型")
                
                # 检查是否所有训练成功的模型都已加载
                if loaded_models < successful_count:
                    logger.warning(f"注意：只有 {loaded_models}/{successful_count} 个训练成功的模型被加载")
            except Exception as e:
                logger.error(f"重新加载模型时出错: {str(e)}", exc_info=True)
            
            if successful_count == len(departments):
                logger.info("所有科室的模型训练成功")
                logger.info("***训练完成***")
                return True
            elif successful_count > 0:
                logger.warning(f"部分科室模型训练成功 ({successful_count}/{len(departments)})")
                logger.info("***训练部分完成***")
                return True
            else:
                logger.error("所有科室模型训练失败")
                return False
            
        except Exception as e:
            logger.error(f"训练所有模型时出错: {str(e)}")
            return False

    def _generate_simulated_training_data(self):
        """生成模拟训练数据用于测试
        
        Returns:
            DataFrame: 模拟的训练数据
        """
        logger.info("生成模拟训练数据")
        
        import numpy as np
        import pandas as pd
        
        # 获取数据库中的科室ID
        try:
            from navigation.models import Department
            dept_ids = list(Department.objects.values_list('id', flat=True))
            logger.info(f"使用数据库中的科室ID生成模拟数据: {dept_ids}")
        except Exception as e:
            logger.error(f"获取数据库科室ID失败: {str(e)}")
            # 如果无法获取科室ID，使用默认值
            dept_ids = [4, 5, 6, 7, 8, 9, 10, 11]
            logger.info(f"使用默认科室ID: {dept_ids}")
        
        # 生成模拟数据
        n_samples = 2000  # 生成足够多的样本
        
        sim_data = []
        for _ in range(n_samples):
            dept_id = np.random.choice(dept_ids)
            queue_count = np.random.randint(0, 20)
            
            # 科室容量
            department_capacity = np.random.randint(5, 15)
            
            # 医生/设备工作效率 (0.5-1.5)
            staff_efficiency = np.random.uniform(0.5, 1.5)
            
            # 设备状态 (0=故障, 1=正常)
            equipment_status = np.random.choice([0, 1], p=[0.1, 0.9])
            
            # 基本模型: 等待时间 = 队列长度 * 每人处理时间 / (效率 * 设备状态) + 随机扰动
            base_processing_time = 15  # 基础处理时间(分钟/人)
            
            # 计算等待时间
            wait_time = queue_count * base_processing_time / (staff_efficiency * (1 if equipment_status == 0 else 2))
            wait_time += np.random.normal(0, 10)  # 添加随机扰动
            
            # 容量因素影响
            capacity_factor = department_capacity / 10.0  # 标准化容量
            wait_time = wait_time / capacity_factor
            
            # 增加时间因素的影响
            hour = np.random.randint(8, 18)
            if hour in [11, 12, 17]:  # 高峰时段
                wait_time *= 1.2
                
            # 增加周末因素的影响
            is_weekend = np.random.choice([0, 1], p=[0.7, 0.3])
            if is_weekend:
                wait_time *= 0.8  # 周末人少一些
                
            # 历史等待时间
            historical_wait_time = wait_time * np.random.uniform(0.8, 1.2)
                
            sim_data.append({
                'department_id': dept_id,
                'queue_count': queue_count,
                'department_capacity': department_capacity,
                'staff_efficiency': staff_efficiency,
                'equipment_status': equipment_status,
                'historical_wait_time': historical_wait_time,
                'hour': hour,
                'day_of_week': np.random.randint(0, 7),
                'is_weekend': is_weekend,
                'actual_wait_time': max(0, wait_time)
            })
            
        df = pd.DataFrame(sim_data)
        
        # 生成时间戳列用于Prophet模型
        current_time = pd.Timestamp.now().floor('D')
        timestamps = []
        
        for _ in range(len(df)):
            # 生成随机的过去时间
            random_hours = np.random.randint(-30*24, 0)  # 过去30天内
            timestamps.append(current_time + pd.Timedelta(hours=random_hours))
        
        df['timestamp'] = timestamps
        df = df.sort_values('timestamp')
        
        # 保存模拟数据
        try:
            data_dir = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'data')
            os.makedirs(data_dir, exist_ok=True)
            df.to_csv(os.path.join(data_dir, 'wait_time_training_data.csv'), index=False)
            logger.info(f"已保存 {len(df)} 条模拟训练数据")
        except Exception as e:
            logger.error(f"保存模拟数据失败: {str(e)}")
            
        return df

    def _train_and_save_model(self, department_id, df, algorithm='xgboost'):
        """训练和保存单个科室的模型
        
        Args:
            department_id: 科室ID
            df: 该科室的训练数据
            algorithm: 使用的算法，可选值: 'xgboost', 'prophet', 'random_forest', 'gradient_boosting', 'linear'
            
        Returns:
            bool: 是否成功训练和保存模型
        """
        logger.info(f"开始训练科室 {department_id} 的模型，使用 {len(df)} 条数据")
        
        # 调用训练方法
        model, metrics = self.train_model(df, department_id=department_id, model_type=algorithm)
        
        if model is None:
            logger.error(f"科室 {department_id} 模型训练失败，返回了None")
            return False
            
        # 训练成功
        mae = metrics.get('mae', 0)
        r2 = metrics.get('r2', 0)
        logger.info(f"科室 {department_id} 模型训练完成，MAE: {mae:.2f}, R²: {r2:.2f}")
        
        # 保存性能指标到JSON文件
        try:
            import json
            
            # 构建性能指标数据
            department_name = None
            try:
                from navigation.models import Department
                dept = Department.objects.filter(id=department_id).first()
                if dept:
                    department_name = dept.name
            except:
                pass
                
            metrics_data = {
                'department_id': department_id,
                'department_name': department_name or f'科室 {department_id}',
                'model_type': algorithm,
                'mae': mae,
                'rmse': metrics.get('rmse', 0),
                'r2': r2,
                'accuracy': 100 - min(100, mae), # 简单估算准确率
                'sample_count': len(df),
                'training_time': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            # 读取现有的指标文件
            metrics_file = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'model_metrics.json')
            all_metrics = {}
            
            if os.path.exists(metrics_file):
                try:
                    with open(metrics_file, 'r') as f:
                        all_metrics = json.load(f)
                except Exception as e:
                    logger.error(f"读取模型性能指标文件时出错: {str(e)}")
            
            # 更新当前科室的指标
            all_metrics[str(department_id)] = metrics_data
            
            # 保存回文件
            with open(metrics_file, 'w') as f:
                json.dump(all_metrics, f, indent=2)
                
            logger.info(f"已保存科室 {department_id} 的性能指标到文件")
            
        except Exception as e:
            logger.error(f"保存性能指标时出错: {str(e)}")
        
        # 生成评估图表
        try:
            if algorithm != 'prophet':
                X, y = self.prepare_features(df)
                self.generate_evaluation_plots(model, X, y, department_id)
        except Exception as e:
            logger.warning(f"生成科室 {department_id} 的评估图表失败: {str(e)}")
        
        return True


# 创建全局实例
model_trainer = ModelTrainer() 