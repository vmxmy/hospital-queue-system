from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
import os
import json
import logging
from datetime import datetime, timedelta
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
from django.urls import reverse
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg, Max, Min
from django.conf import settings
from celery.result import AsyncResult
from django.views.decorators.csrf import csrf_exempt
from .models import Department, Queue
from .ml.models import prediction_service
from .ml.data_collector import data_collector
from .ml.tasks import train_wait_time_models, update_predicted_wait_times

logger = logging.getLogger(__name__)

@method_decorator(staff_member_required, name='dispatch')
class MLDashboardView(TemplateView):
    template_name = 'admin/navigation/ml_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 添加Django管理界面需要的上下文变量
        context['title'] = '机器学习模型训练与监控'
        context['subtitle'] = '数据收集与模型训练'
        context['is_nav_sidebar_enabled'] = True
        context['site_title'] = '医院检验智能排队引导系统'
        context['site_header'] = '医院检验智能排队引导系统管理'
        context['has_permission'] = True
        
        # 添加缺少的Django管理界面变量
        context['is_popup'] = False
        context['is_nav_sidebar_enabled'] = True
        context['site_url'] = '/'
        context['available_apps'] = []
        context['app_list'] = []
        
        # 模型状态
        is_model_ready = prediction_service.is_ready()
        model_status = "就绪" if is_model_ready else "未就绪"
        
        # 可用模型
        available_departments = prediction_service.get_available_departments()
        departments_with_models = Department.objects.filter(id__in=available_departments)
        
        # 训练数据
        training_data = data_collector.get_training_data()
        training_data_count = len(training_data) if training_data is not None else 0
        
        # 上次训练时间
        model_dir = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'trained_models')
        last_trained = None
        if os.path.exists(model_dir):
            model_files = [os.path.join(model_dir, f) for f in os.listdir(model_dir) if f.endswith('.pkl')]
            if model_files:
                last_trained = datetime.fromtimestamp(max(os.path.getmtime(f) for f in model_files))
        
        # 模型性能指标
        model_metrics = prediction_service.get_performance_metrics()
        
        # 等待时间分布
        wait_times = Queue.objects.filter(
            status='completed', 
            actual_wait_time__isnull=False,
            created_at__gte=timezone.now() - timedelta(days=30)
        ).values_list('actual_wait_time', flat=True)
        
        # 等待时间分组
        bins = [0, 5, 10, 15, 20, 30, 45, 60, 90, 120, 180]
        wait_time_data = [0] * (len(bins) - 1)
        wait_time_labels = []
        
        for i in range(len(bins) - 1):
            min_time = bins[i]
            max_time = bins[i+1]
            label = f"{min_time}-{max_time}"
            wait_time_labels.append(label)
            
            # 计算该范围内的等待时间数量
            for wait_time in wait_times:
                if min_time <= wait_time < max_time:
                    wait_time_data[i] += 1
        
        # 读取训练日志
        training_logs = []
        log_file = os.path.join(settings.BASE_DIR, 'logs', 'ml_training.log')
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                for line in f.readlines()[-50:]:  # 最近50行日志
                    if line.strip():
                        try:
                            # 使用更灵活的方式解析日志行
                            parts = line.split(' ', 3)
                            if len(parts) >= 4:
                                level = parts[0].lower()
                                timestamp = parts[1] + ' ' + parts[2]
                                message = parts[3].strip()
                            else:
                                # 如果无法正确分割，将整行作为消息
                                level = 'INFO'
                                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                                message = line.strip()
                                
                            # 处理消息中可能的空时间戳标记
                            if message.startswith('[]'):
                                message = message.strip()
                                
                            training_logs.append({
                                'level': level,
                                'timestamp': timestamp,
                                'message': message
                            })
                        except Exception as e:
                            logger.error(f"解析日志行时出错: {str(e)}, 原始日志行: {line}")
                            # 确保即使解析出错也添加日志条目
                            training_logs.append({
                                'level': 'info',
                                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'message': line.strip()
                            })
        
        context.update({
            'is_model_ready': is_model_ready,
            'model_status': model_status,
            'available_models': len(available_departments),
            'departments_with_models': departments_with_models,
            'training_data_count': training_data_count,
            'last_trained': last_trained,
            'model_metrics': model_metrics,
            'wait_time_labels': json.dumps(wait_time_labels),
            'wait_time_data': json.dumps(wait_time_data),
            'training_logs': training_logs,
            'now': timezone.now()
        })
        
        return context


@staff_member_required
@csrf_exempt
def ml_collect_data(request):
    """收集模型训练数据"""
    logger.info(f"收到收集数据请求: {request.method} {request.content_type}")
    if request.method == 'POST':
        try:
            # 获取天数参数，默认30天
            days = 30
            
            # 尝试从GET参数获取days
            if request.GET.get('days'):
                try:
                    days = int(request.GET.get('days'))
                    logger.info(f"使用GET参数的days值: {days}")
                except (ValueError, TypeError):
                    logger.warning(f"无效的days参数: {request.GET.get('days')}, 使用默认值30")
            
            # 设置请求属性，避免Debug Toolbar尝试处理
            request.is_ajax = lambda: True
            
            # 收集训练数据
            logger.info(f"开始收集{days}天的历史数据")
            training_data = data_collector.collect_historical_data(days=days)
            
            # 记录日志
            data_count = len(training_data) if training_data is not None else 0
            logger.info(f"成功收集了 {data_count} 条训练数据")
            
            result = {
                'success': True,
                'message': f'成功收集了 {data_count} 条训练数据'
            }
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"收集训练数据时出错: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'收集数据失败: {str(e)}'
            }, status=500)
    else:
        logger.warning(f"请求方法不支持: {request.method}")
        return JsonResponse({
            'success': False,
            'message': '只支持POST请求'
        }, status=405)


@staff_member_required
@csrf_exempt
def ml_train_model(request):
    """开始训练机器学习模型"""
    logger.info(">>>训练开始>>>")
    
    # 解析请求体，获取算法参数
    algorithm = None
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
            algorithm = data.get('algorithm', 'xgboost')  # 默认使用xgboost
            logger.info(f"选择的算法: {algorithm}")
        except json.JSONDecodeError:
            logger.warning("无法解析JSON请求体，使用默认算法")
            algorithm = 'xgboost'
    else:
        algorithm = 'xgboost'  # 兼容旧版本的请求
    
    try:
        # 尝试使用Celery任务来训练模型
        task = train_wait_time_models.delay(algorithm=algorithm)
        task_id = task.id
        logger.info(f"已提交模型训练任务，任务ID: {task_id}，算法: {algorithm}")
        return JsonResponse({'status': 'success', 'task_id': task_id})
    except Exception as e:
        logger.warning(f"无法连接到Celery，将在本地执行训练: {str(e)}")
        
        # 本地执行训练
        try:
            from navigation.ml.trainer import model_trainer
            from navigation.ml.data_collector import data_collector
            
            # 收集训练数据
            try:
                logger.info("开始收集模型训练数据")
                df = data_collector.get_training_data()
                training_data_count = len(df)
                logger.info(f"成功收集到 {training_data_count} 条训练数据")
                logger.info(f"开始训练等待时间预测模型，使用 {training_data_count} 条训练数据，算法: {algorithm}")
            except Exception as data_error:
                logger.error(f"收集训练数据失败: {str(data_error)}")
                df = None
            
            # 训练模型
            success = model_trainer.train_all_models(df, algorithm=algorithm)
            
            if success:
                logger.info(f"等待时间预测模型训练完成，算法: {algorithm}")
                logger.info("***训练完成***")
                return JsonResponse({
                    'status': 'success', 
                    'task_id': 'local_train',
                    'message': f'模型训练成功，使用算法: {algorithm}'
                })
            else:
                logger.error(f"等待时间预测模型训练失败，算法: {algorithm}")
                return JsonResponse({
                    'status': 'error',
                    'message': '模型训练失败，请查看日志了解详情'
                })
                
        except Exception as local_error:
            logger.error(f"本地训练模型失败: {str(local_error)}")
            return JsonResponse({
                'status': 'error',
                'message': f'训练失败: {str(local_error)}'
            })


@staff_member_required
def ml_check_status(request):
    """检查训练任务状态"""
    task_id = request.GET.get('task_id')
    if not task_id:
        return JsonResponse({
            'success': False,
            'message': '缺少task_id参数'
        }, status=400)
    
    try:
        # 处理本地任务（非Celery任务）
        if task_id == 'local_train':
            # 读取最新日志
            logs = []
            log_file = os.path.join(settings.BASE_DIR, 'logs', 'ml_training.log')
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        # 只返回最近10行日志
                        for line in lines[-10:]:
                            if line.strip():
                                # 使用更灵活的方式解析日志行
                                try:
                                    parts = line.split(' ', 3)
                                    if len(parts) >= 4:
                                        level = parts[0].lower()
                                        timestamp = parts[1] + ' ' + parts[2]
                                        message = parts[3].strip()
                                    else:
                                        # 如果无法正确分割，将整行作为消息
                                        level = 'INFO'
                                        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                                        message = line.strip()
                                except Exception:
                                    level = 'INFO'
                                    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                                    message = line.strip()
                                
                                logs.append({
                                    'level': level,
                                    'timestamp': timestamp,
                                    'message': message
                                })
            
            # 检查模型文件是否已更新
            is_completed = False
            model_dir = os.path.join(settings.BASE_DIR, 'navigation', 'ml', 'trained_models')
            if os.path.exists(model_dir):
                model_files = [os.path.join(model_dir, f) for f in os.listdir(model_dir) if f.endswith('.pkl')]
                # 如果最近5分钟内有模型文件更新，认为任务已完成
                if model_files and any(os.path.getmtime(f) > (timezone.now().timestamp() - 300) for f in model_files):
                    is_completed = True
            
            # 返回本地任务状态
            return JsonResponse({
                'success': True,
                'status': 'SUCCESS' if is_completed else 'PROGRESS',
                'progress': 100 if is_completed else 75,
                'logs': logs,
                'message': '本地训练已完成' if is_completed else '本地训练进行中...'
            })
        
        # 处理常规Celery任务
        task_result = AsyncResult(task_id)
        
        # 读取最新日志
        logs = []
        log_file = os.path.join(settings.BASE_DIR, 'logs', 'ml_training.log')
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    # 只返回最近10行日志
                    for line in lines[-10:]:
                        if line.strip():
                            # 使用更灵活的方式解析日志行
                            try:
                                parts = line.split(' ', 3)
                                if len(parts) >= 4:
                                    level = parts[0].lower()
                                    timestamp = parts[1] + ' ' + parts[2]
                                    message = parts[3].strip()
                                else:
                                    # 如果无法正确分割，将整行作为消息
                                    level = 'INFO'
                                    timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                                    message = line.strip()
                            except Exception:
                                level = 'INFO'
                                timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
                                message = line.strip()
                                
                            logs.append({
                                'level': level,
                                'timestamp': timestamp,
                                'message': message
                            })
        
        # 计算进度
        progress = 0
        if task_result.state == 'SUCCESS':
            progress = 100
        elif task_result.state == 'STARTED':
            progress = 25
        elif task_result.state == 'PROGRESS':
            progress = task_result.info.get('progress', 50)
            
        return JsonResponse({
            'success': True,
            'status': task_result.state,
            'progress': progress,
            'logs': logs
        })
    except Exception as e:
        logger.error(f"检查任务状态时出错: {str(e)}")
        # 发生错误也要尝试读取日志
        logs = []
        try:
            log_file = os.path.join(settings.BASE_DIR, 'logs', 'ml_training.log')
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    if lines:
                        for line in lines[-5:]:
                            logs.append({'level': 'info', 'message': line.strip()})
        except:
            pass
            
        return JsonResponse({
            'success': False,
            'message': f'检查状态失败: {str(e)}',
            'logs': logs
        }, status=500)


@staff_member_required
def ml_update_wait_times(request):
    """更新所有队列的等待时间预测"""
    if request.method == 'POST':
        try:
            # 启动Celery任务进行等待时间更新
            task = update_predicted_wait_times.delay()
            
            logger.info(f"启动更新队列等待时间任务: {task.id}")
            
            return JsonResponse({
                'success': True,
                'message': '队列等待时间更新任务已启动',
                'task_id': task.id
            })
        except Exception as e:
            logger.error(f"启动更新等待时间任务时出错: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'启动更新失败: {str(e)}'
            }, status=500)
    else:
        return JsonResponse({
            'success': False,
            'message': '只支持POST请求'
        }, status=405) 