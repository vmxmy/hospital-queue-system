from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.shortcuts import get_object_or_404
from rest_framework import status

class QueueModelReady(APIView):
    """
    检查机器学习模型是否就绪的API
    """
    def get(self, request):
        try:
            from navigation.ml import prediction_service
            
            # 检查模型是否就绪
            model_status = {
                'ready': prediction_service.is_ready(),
                'departments': prediction_service.get_available_departments()
            }
            
            return Response(model_status)
        except ImportError:
            return Response({'ready': False, 'error': '机器学习模块未启用'})
        except Exception as e:
            return Response({'ready': False, 'error': str(e)})


class TrainWaitTimeModels(APIView):
    """
    触发等待时间预测模型训练的API
    需要管理员权限
    """
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        try:
            from navigation.ml.tasks import train_wait_time_models
            
            # 获取请求中的算法参数
            algorithm = request.data.get('algorithm', 'xgboost')
            
            # 异步启动训练任务
            task = train_wait_time_models.delay(algorithm=algorithm)
            
            return Response({
                'status': 'success',
                'message': f'模型训练任务已启动，使用算法: {algorithm}',
                'task_id': task.id
            })
        except ImportError:
            return Response({
                'status': 'error',
                'message': '机器学习模块未启用'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'启动模型训练失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WaitTimePredictionMetrics(APIView):
    """
    获取等待时间预测模型性能指标的API
    仅管理员可用
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        try:
            from navigation.ml import prediction_service
            
            # 获取各科室模型的性能指标
            metrics = prediction_service.get_performance_metrics()
            
            if not metrics:
                return Response({
                    'status': 'warning',
                    'message': '模型尚未训练或没有性能指标'
                })
            
            return Response({
                'status': 'success',
                'metrics': metrics
            })
        except ImportError:
            return Response({
                'status': 'error',
                'message': '机器学习模块未启用'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'获取模型性能指标失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateQueueWaitTime(APIView):
    """
    使用机器学习模型更新单个队列等待时间的API
    """
    def post(self, request, queue_id):
        try:
            # 获取队列对象
            queue = get_object_or_404(Queue, id=queue_id)
            
            # 使用机器学习更新等待时间
            success = queue.update_wait_time_with_ml()
            
            if success:
                return Response({
                    'status': 'success',
                    'message': '等待时间已更新',
                    'queue_id': queue.id,
                    'estimated_wait_time': queue.estimated_wait_time
                })
            else:
                return Response({
                    'status': 'warning',
                    'message': '使用机器学习更新失败，已使用默认方法',
                    'queue_id': queue.id,
                    'estimated_wait_time': queue.estimated_wait_time
                })
                
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'更新等待时间失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UpdateAllQueueWaitTimes(APIView):
    """
    使用机器学习模型更新所有等待中队列的等待时间
    """
    def post(self, request):
        try:
            from navigation.ml.tasks import update_predicted_wait_times
            
            # 异步启动更新任务
            task = update_predicted_wait_times.delay()
            
            return Response({
                'status': 'success',
                'message': '所有队列等待时间更新任务已启动',
                'task_id': task.id
            })
        except ImportError:
            return Response({
                'status': 'error',
                'message': '机器学习模块未启用'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'启动队列更新任务失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 