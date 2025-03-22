"""
机器学习相关的Celery任务
"""
import logging
import os
from celery import shared_task, current_task
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import traceback

from .models import prediction_service
from .data_collector import data_collector
from .trainer import model_trainer
from navigation.models import Department, Examination
from navigation.ml.data_collector import QueueDataCollector
from navigation.ml.prophet_predictor import get_prophet_predictor, ProphetWaitTimePredictor

# 配置日志
logger = logging.getLogger(__name__)

# 确保日志目录存在
log_dir = os.path.join(settings.BASE_DIR, 'logs')
os.makedirs(log_dir, exist_ok=True)

# 配置日志输出到文件，使用固定的时间戳格式
log_handler = logging.FileHandler(os.path.join(log_dir, 'ml_training.log'))
formatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s', '%Y-%m-%d %H:%M:%S')
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)
logger.setLevel(logging.DEBUG)


@shared_task(bind=True)
def train_wait_time_models(self, algorithm='xgboost', *args, **kwargs):
    """
    训练等待时间预测模型的Celery任务
    
    Args:
        algorithm: 使用的算法，可选值: 'xgboost', 'prophet', 'random_forest', 'gradient_boosting', 'linear'
    """
    logger.info(f">>>训练开始，使用算法: {algorithm}>>>")
    self.update_state(state="PROGRESS", meta={"progress": 0, "message": "开始训练"})
    
    # 导入训练需要的模块
    from navigation.ml.trainer import model_trainer
    from navigation.ml.data_collector import data_collector
    
    try:
        # 更新任务状态为10%进度
        self.update_state(state="PROGRESS", meta={"progress": 10, "message": "开始收集训练数据"})
        logger.info("开始收集模型训练数据")
        
        # 尝试获取训练数据
        try:
            df = data_collector.get_training_data()
            training_data_count = len(df)
            logger.info(f"成功收集到 {training_data_count} 条训练数据")
        except Exception as data_error:
            # 数据收集失败，使用模拟数据
            logger.error(f"收集训练数据失败: {str(data_error)}")
            logger.info("将使用模拟数据进行训练")
            df = None
            
        # 更新任务状态为30%进度
        try:
            self.update_state(state="PROGRESS", meta={"progress": 30, "message": f"开始训练模型 (算法: {algorithm})"})
        except Exception as update_error:
            logger.warning(f"更新任务状态失败: {str(update_error)}")
        
        logger.info(f"开始训练等待时间预测模型，使用算法: {algorithm}")
        # 训练模型
        success = model_trainer.train_all_models(df, algorithm=algorithm)
        
        # 更新任务状态为100%进度
        try:
            self.update_state(state="PROGRESS", meta={"progress": 100, "message": "训练完成"})
        except Exception as update_error:
            logger.warning(f"更新任务状态失败: {str(update_error)}")
            
        if success:
            logger.info(f"等待时间预测模型训练完成，使用算法: {algorithm}")
            logger.info("***训练完成***")
            return {"success": True, "message": f"模型训练成功，使用算法: {algorithm}"}
        else:
            logger.error(f"等待时间预测模型训练失败，使用算法: {algorithm}")
            return {"success": False, "message": "模型训练失败"}
            
    except Exception as e:
        logger.error(f"训练模型时发生错误: {str(e)}")
        logger.exception("详细错误信息:")
        try:
            self.update_state(state="FAILURE", meta={"progress": 0, "message": f"训练失败: {str(e)}"})
        except Exception:
            pass
        return {"success": False, "message": f"训练失败: {str(e)}"}


@shared_task
def update_predicted_wait_times():
    """
    使用机器学习模型更新所有等待队列的预测等待时间
    """
    from navigation.models import Queue, Department, Equipment
    
    try:
        # 更新任务状态为开始
        if current_task:
            current_task.update_state(state='PROGRESS', meta={'progress': 10})
        
        # 获取需要更新的队列
        waiting_queues = Queue.objects.filter(status='waiting')
        
        # 获取实时数据
        logger.info("开始收集实时数据")
        real_time_data = data_collector.collect_real_time_data()
        
        # 更新进度
        if current_task:
            current_task.update_state(state='PROGRESS', meta={'progress': 40})
        
        logger.info(f"开始更新 {waiting_queues.count()} 个队列的预计等待时间")
        
        updated_count = 0
        total_count = waiting_queues.count()
        for i, queue in enumerate(waiting_queues):
            dept_id = queue.department_id
            if dept_id in real_time_data:
                dept_data = real_time_data[dept_id]
                
                # 获取队列在科室中的位置（前面有多少人）
                position = queue.get_position() - 1  # 减1是因为get_position返回的是含自己的位置
                
                # 如果队列在前面，使用实际的排队人数；否则使用科室总排队数
                queue_count = position if position >= 0 else dept_data['queue_count']
                
                # 使用模型预测等待时间
                predicted_time = prediction_service.predict_wait_time(
                    department_id=dept_id,
                    queue_count=queue_count,
                    equipment_status=dept_data['equipment_status'],
                    priority=queue.priority
                )
                
                # 更新队列的预计等待时间
                old_time = queue.estimated_wait_time
                queue.estimated_wait_time = round(predicted_time)
                queue.save(update_fields=['estimated_wait_time'])
                
                # 记录明显变化的预测
                if abs(old_time - queue.estimated_wait_time) > 5:
                    logger.info(f"队列 {queue.id} 的等待时间从 {old_time} 更新为 {queue.estimated_wait_time} 分钟")
                
                updated_count += 1
            
            # 每10%更新一次进度
            if current_task and total_count > 0 and i % max(1, int(total_count/10)) == 0:
                progress = 40 + int(50 * i / total_count)
                current_task.update_state(state='PROGRESS', meta={'progress': progress})
        
        logger.info(f"成功更新 {updated_count} 个队列的预计等待时间")
        
        # 最终更新进度为100%
        if current_task:
            current_task.update_state(state='PROGRESS', meta={'progress': 100})
            
        return f"更新了 {updated_count} 个队列"
        
    except Exception as e:
        logger.error(f"更新预测等待时间出错: {str(e)}")
        return f"错误: {str(e)}"


@shared_task(name="train-prophet-models")
def train_prophet_models():
    """
    训练所有科室和检查项目的Prophet模型
    """
    logger.info("开始训练Prophet模型")
    
    try:
        # 获取数据收集器
        collector = QueueDataCollector(days_lookback=30)
        
        # 训练全局模型
        train_global_model(collector)
        
        # 训练各科室模型
        train_department_models(collector)
        
        # 训练各检查项目模型
        train_examination_models(collector)
        
        logger.info("所有Prophet模型训练完成")
        return {"status": "success", "message": "所有Prophet模型训练完成"}
        
    except Exception as e:
        error_msg = f"训练Prophet模型出错: {str(e)}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())
        return {"status": "error", "message": error_msg}

def train_global_model(collector):
    """
    训练全局模型
    
    参数:
    - collector: 数据收集器实例
    """
    try:
        # 准备全局数据
        global_data = collector.prepare_prophet_data()
        
        if global_data.empty:
            logger.warning("没有全局历史数据可用于训练Prophet模型")
            return False
        
        # 获取全局预测器
        predictor = get_prophet_predictor()
        
        # 训练模型
        success = predictor.train(global_data)
        
        if success:
            logger.info("全局Prophet模型训练成功")
        else:
            logger.warning("全局Prophet模型训练失败")
        
        return success
        
    except Exception as e:
        logger.error(f"训练全局Prophet模型出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def train_department_models(collector):
    """
    训练科室级别模型
    
    参数:
    - collector: 数据收集器实例
    """
    try:
        # 获取所有科室
        departments = Department.objects.all()
        
        success_count = 0
        fail_count = 0
        
        for dept in departments:
            try:
                # 准备科室数据
                dept_data = collector.prepare_prophet_data(department_id=dept.id)
                
                if dept_data.empty:
                    logger.warning(f"科室 '{dept.name}' (ID: {dept.id}) 没有历史数据可用于训练Prophet模型")
                    continue
                
                # 获取科室预测器
                predictor = get_prophet_predictor(department_id=dept.id)
                
                # 训练模型
                success = predictor.train(dept_data)
                
                if success:
                    logger.info(f"科室 '{dept.name}' (ID: {dept.id}) Prophet模型训练成功")
                    success_count += 1
                else:
                    logger.warning(f"科室 '{dept.name}' (ID: {dept.id}) Prophet模型训练失败")
                    fail_count += 1
                    
            except Exception as e:
                logger.error(f"训练科室 '{dept.name}' (ID: {dept.id}) Prophet模型出错: {str(e)}")
                fail_count += 1
        
        logger.info(f"科室模型训练完成: {success_count}个成功, {fail_count}个失败")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"训练科室Prophet模型出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def train_examination_models(collector):
    """
    训练检查项目级别模型
    
    参数:
    - collector: 数据收集器实例
    """
    try:
        # 获取所有检查项目
        examinations = Examination.objects.all()
        
        success_count = 0
        fail_count = 0
        
        for exam in examinations:
            try:
                # 准备检查项目数据
                exam_data = collector.prepare_prophet_data(examination_id=exam.id)
                
                if exam_data.empty:
                    logger.warning(f"检查项目 '{exam.name}' (ID: {exam.id}) 没有历史数据可用于训练Prophet模型")
                    continue
                
                # 获取检查项目预测器
                predictor = get_prophet_predictor(examination_id=exam.id)
                
                # 训练模型
                success = predictor.train(exam_data)
                
                if success:
                    logger.info(f"检查项目 '{exam.name}' (ID: {exam.id}) Prophet模型训练成功")
                    success_count += 1
                else:
                    logger.warning(f"检查项目 '{exam.name}' (ID: {exam.id}) Prophet模型训练失败")
                    fail_count += 1
                    
            except Exception as e:
                logger.error(f"训练检查项目 '{exam.name}' (ID: {exam.id}) Prophet模型出错: {str(e)}")
                fail_count += 1
        
        logger.info(f"检查项目模型训练完成: {success_count}个成功, {fail_count}个失败")
        return success_count > 0
        
    except Exception as e:
        logger.error(f"训练检查项目Prophet模型出错: {str(e)}")
        logger.error(traceback.format_exc())
        return False 