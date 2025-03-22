from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import admin_views
from .views import (
    HomePageView, 
    QueueInfoView,
    PatientDetailView,
    QueueStatusView,
    DepartmentListView,
    AddQueueView,
)

router = DefaultRouter()
router.register(r'patients', views.PatientViewSet)
router.register(r'departments', views.DepartmentViewSet)
router.register(r'equipment', views.EquipmentViewSet)
router.register(r'examinations', views.ExaminationViewSet)
router.register(r'queues', views.QueueViewSet)
router.register(r'notification-templates', views.NotificationTemplateViewSet)

app_name = 'navigation'  # 添加应用命名空间

urlpatterns = [
    # API 接口
    path('api/', include(router.urls)),
    
    # 主页视图
    path('', views.index, name='index'),
    
    # 科室列表
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    
    # 队列信息
    path('queue/<str:department_code>/', views.QueueInfoView.as_view(), name='queue_info'),
    
    # 病人详情
    path('patient/<str:patient_id>/', views.PatientDetailView.as_view(), name='patient_detail'),
    
    # 队列状态 - 实时数据
    path('queue/status/<str:department_code>/', views.QueueStatusView.as_view(), name='queue_status'),
    
    # 添加队列
    path('queue/add/', views.AddQueueView.as_view(), name='add_queue'),
    
    # 管理相关视图
    path('admin/ml/dashboard/', admin_views.MLDashboardView.as_view(), name='admin_ml_dashboard'),
    path('admin/ml/collect-data/', admin_views.ml_collect_data, name='admin_ml_collect_data'),
    path('admin/ml/train-model/', admin_views.ml_train_model, name='admin_ml_train_model'),
    path('admin/ml/check-status/', admin_views.ml_check_status, name='admin_ml_check_status'),
    path('admin/ml/update-wait-times/', admin_views.ml_update_wait_times, name='admin_ml_update_wait_times'),
    
    # API 路由
    path('api/departments/<int:department_id>/examinations/', views.department_examinations, name='department_examinations'),
    path('api/departments/<int:department_id>/equipment/', views.department_equipment, name='department_equipment'),
    path('api/examinations/<int:examination_id>/equipment/', views.examination_equipment, name='examination_equipment'),
] 