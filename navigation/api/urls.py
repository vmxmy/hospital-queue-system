from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    QueueModelReady, TrainWaitTimeModels, WaitTimePredictionMetrics,
    UpdateQueueWaitTime, UpdateAllQueueWaitTimes
)

router = DefaultRouter()
# 注册你的路由器...

urlpatterns = [
    path('', include(router.urls)),
    
    # 机器学习模型相关API路由
    path('ml/model-status/', QueueModelReady.as_view(), name='ml-model-status'),
    path('ml/train-models/', TrainWaitTimeModels.as_view(), name='ml-train-models'),
    path('ml/model-metrics/', WaitTimePredictionMetrics.as_view(), name='ml-model-metrics'),
    path('ml/update-queue-wait-time/<int:queue_id>/', UpdateQueueWaitTime.as_view(), name='ml-update-queue-wait-time'),
    path('ml/update-all-wait-times/', UpdateAllQueueWaitTimes.as_view(), name='ml-update-all-wait-times'),
] 