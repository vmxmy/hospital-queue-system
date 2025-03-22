from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q, F, Count
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from datetime import timedelta
from django.views.generic import TemplateView, ListView, DetailView
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect

from .models import (
    Patient, Department, Equipment, Examination, Queue,
    NotificationTemplate, NotificationCategory, NotificationStats
)
from .serializers import (
    PatientSerializer,
    DepartmentSerializer,
    EquipmentSerializer,
    ExaminationSerializer,
    QueueSerializer,
    NotificationTemplateSerializer,
)


# 首页视图
def index(request):
    """首页视图"""
    departments = Department.objects.filter(is_active=True)
    
    # 统计每个科室当前排队的人数
    for dept in departments:
        dept.waiting_count = dept.queue_set.filter(status='waiting').count()
    
    # 获取最近的队列
    recent_queues = Queue.objects.filter(
        status__in=['waiting', 'processing']
    ).order_by('-priority', 'enter_time')
    
    # 为每个等待中的队列添加ahead_count属性
    for queue in recent_queues:
        if queue.status == 'waiting':
            try:
                # 尝试使用ahead_count属性
                queue.ahead_count_value = queue.ahead_count
            except AttributeError:
                # 如果属性不存在，直接计算
                queue.ahead_count_value = Queue.objects.filter(
                    department=queue.department,
                    status='waiting',
                    enter_time__lt=queue.enter_time
                ).count()
    
    context = {
        'departments': departments,
        'recent_queues': recent_queues,
        'stats': {
            'total_patients': Queue.objects.filter(status__in=['waiting', 'processing']).count(),
            'waiting_queues': Queue.objects.filter(status='waiting').count(),
            'processing_queues': Queue.objects.filter(status='processing').count(),
            'completed_today': Queue.objects.filter(
                status='completed', 
                end_time__date=timezone.now().date()
            ).count(),
        }
    }
    return render(request, 'navigation/index.html', context)


# 基于类的视图
class HomePageView(TemplateView):
    """主页视图"""
    template_name = 'navigation/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取所有活跃科室
        departments = Department.objects.filter(is_active=True)
        
        # 统计每个科室当前排队的人数
        for dept in departments:
            dept.waiting_count = dept.queue_set.filter(status='waiting').count()
        
        # 获取最近的队列
        recent_queues = Queue.objects.filter(
            status__in=['waiting', 'processing']
        ).order_by('-priority', 'enter_time')
        
        # 添加统计数据
        context.update({
            'departments': departments,
            'recent_queues': recent_queues,
            'stats': {
                'total_patients': Queue.objects.filter(status__in=['waiting', 'processing']).count(),
                'waiting_queues': Queue.objects.filter(status='waiting').count(),
                'processing_queues': Queue.objects.filter(status='processing').count(),
                'completed_today': Queue.objects.filter(
                    status='completed', 
                    end_time__date=timezone.now().date()
                ).count(),
            }
        })
        
        return context


class DepartmentListView(ListView):
    """科室列表视图"""
    model = Department
    template_name = 'navigation/department_list.html'
    context_object_name = 'departments'
    
    def get_queryset(self):
        return Department.objects.filter(is_active=True)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 为每个科室添加等待人数
        for dept in context['departments']:
            dept.waiting_count = dept.queue_set.filter(status='waiting').count()
            
        return context


class QueueInfoView(DetailView):
    """队列信息视图"""
    model = Department
    template_name = 'navigation/queue_info.html'
    context_object_name = 'department'
    
    def get_object(self):
        return Department.objects.get(code=self.kwargs['department_code'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取当前科室的队列信息
        department = self.get_object()
        queues = department.queue_set.filter(
            status__in=['waiting', 'processing']
        ).order_by('-priority', 'enter_time')
        
        context.update({
            'queues': queues,
            'waiting_count': queues.filter(status='waiting').count(),
            'processing_count': queues.filter(status='processing').count(),
        })
        
        return context


class PatientDetailView(DetailView):
    """病人详情视图"""
    model = Patient
    template_name = 'navigation/patient_detail.html'
    context_object_name = 'patient'
    
    def get_object(self):
        return Patient.objects.get(patient_id=self.kwargs['patient_id'])
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取病人的队列信息
        patient = self.get_object()
        recent_queues = patient.queue_set.order_by('-enter_time')
        
        context.update({
            'recent_queues': recent_queues,
        })
        
        return context


class QueueStatusView(TemplateView):
    """队列状态视图 - 提供实时数据"""
    
    def get(self, request, *args, **kwargs):
        department_code = kwargs.get('department_code')
        
        try:
            department = Department.objects.get(code=department_code)
            
            # 获取当前队列状态
            waiting_queues = department.queue_set.filter(status='waiting')
            processing_queues = department.queue_set.filter(status='processing')
            
            # 计算平均等待时间 (已完成的队列)
            completed_queues = department.queue_set.filter(
                status='completed',
                enter_time__gt=timezone.now() - timedelta(days=7)  # 最近7天
            )
            
            avg_wait_time = 0
            if completed_queues.exists():
                total_wait_time = sum([(q.start_time - q.enter_time).total_seconds() for q in completed_queues if q.start_time])
                avg_wait_time = total_wait_time / completed_queues.count() / 60  # 转换为分钟
            
            # 构建响应数据
            data = {
                'department': {
                    'name': department.name,
                    'code': department.code,
                },
                'queue_status': {
                    'waiting_count': waiting_queues.count(),
                    'processing_count': processing_queues.count(),
                    'avg_wait_time': round(avg_wait_time, 1),  # 平均等待时间（分钟）
                },
                'waiting_queues': [
                    {
                        'queue_id': q.id,
                        'patient_name': q.patient.name,
                        'patient_id': q.patient.patient_id,
                        'priority': q.priority,
                        'enter_time': q.enter_time.strftime('%H:%M:%S'),
                        'enter_time_raw': q.enter_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'estimated_time': q.estimated_wait_time,
                    }
                    for q in waiting_queues.order_by('-priority', 'enter_time')
                ],
                'processing_queues': [
                    {
                        'queue_id': q.id,
                        'patient_name': q.patient.name,
                        'patient_id': q.patient.patient_id,
                        'priority': q.priority,
                        'enter_time': q.enter_time.strftime('%H:%M:%S'),
                        'enter_time_raw': q.enter_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'start_time': q.start_time.strftime('%H:%M:%S') if q.start_time else None,
                        'start_time_raw': q.start_time.strftime('%Y-%m-%d %H:%M:%S') if q.start_time else None,
                    }
                    for q in processing_queues.order_by('-priority', 'start_time')
                ],
                'timestamp': timezone.now().strftime('%Y-%m-%d %H:%M:%S'),
            }
            
            return JsonResponse(data)
            
        except Department.DoesNotExist:
            return JsonResponse({'error': '科室不存在'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class PatientViewSet(viewsets.ModelViewSet):
    """患者视图集"""
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

    @action(detail=True, methods=['get'])
    def queues(self, request, pk=None):
        """获取患者的排队记录"""
        patient = self.get_object()
        active_queues = patient.queue_set.filter(status__in=['waiting', 'processing'])
        history_queues = patient.queue_set.filter(status__in=['completed', 'cancelled']).order_by('-enter_time')
        
        return Response({
            'active': QueueSerializer(active_queues, many=True).data,
            'history': QueueSerializer(history_queues, many=True).data
        })


class DepartmentViewSet(viewsets.ModelViewSet):
    """科室视图集"""
    queryset = Department.objects.all()
    serializer_class = DepartmentSerializer

    @action(detail=True, methods=['get'])
    def queues(self, request, pk=None):
        """获取科室当前排队情况"""
        department = self.get_object()
        queues = department.queue_set.filter(status='waiting').order_by('-priority', 'enter_time')
        
        return Response(QueueSerializer(queues, many=True).data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """获取科室统计数据"""
        department = self.get_object()
        today = timezone.now().date()
        
        return Response({
            'waiting_count': department.queue_set.filter(status='waiting').count(),
            'processing_count': department.queue_set.filter(status='processing').count(),
            'completed_today': department.queue_set.filter(status='completed', end_time__date=today).count(),
            'average_wait_time': department.get_average_wait_time(),
        })


class EquipmentViewSet(viewsets.ModelViewSet):
    """设备视图集"""
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer

    @action(detail=True, methods=['post'])
    def schedule_maintenance(self, request, pk=None):
        """安排设备维护"""
        equipment = self.get_object()
        maintenance_date = request.data.get('maintenance_date')
        
        try:
            maintenance_date = timezone.datetime.strptime(
                maintenance_date, '%Y-%m-%d'
            ).date()
            equipment.schedule_maintenance(maintenance_date)
            return Response({'status': 'maintenance scheduled'})
        except (ValueError, TypeError):
            return Response(
                {'error': 'Invalid date format. Use YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """更新设备状态"""
        equipment = self.get_object()
        new_status = request.data.get('status')
        
        if new_status not in dict(Equipment.STATUS_CHOICES):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        equipment.update_status(new_status)
        return Response({'status': 'updated'})

    @action(detail=True, methods=['get'])
    def queues(self, request, pk=None):
        """获取设备当前排队情况"""
        equipment = self.get_object()
        queues = equipment.queue_set.filter(status='waiting').order_by('-priority', 'enter_time')
        
        return Response(QueueSerializer(queues, many=True).data)


class ExaminationViewSet(viewsets.ModelViewSet):
    """检查项目视图集"""
    queryset = Examination.objects.all()
    serializer_class = ExaminationSerializer

    @action(detail=True, methods=['get'])
    def wait_time(self, request, pk=None):
        """获取检查项目等待时间"""
        examination = self.get_object()
        department_id = request.query_params.get('department')
        
        if department_id:
            try:
                department = Department.objects.get(id=department_id)
                wait_time = examination.estimate_wait_time(department)
            except Department.DoesNotExist:
                return Response(
                    {'error': 'Department not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            wait_time = examination.estimate_wait_time()
        
        return Response({'estimated_wait_time': wait_time})


class QueueViewSet(viewsets.ModelViewSet):
    """排队队列视图集"""
    queryset = Queue.objects.all()
    serializer_class = QueueSerializer

    def get_queryset(self):
        """根据查询参数过滤队列"""
        queryset = Queue.objects.all()
        status = self.request.query_params.get('status', None)
        department = self.request.query_params.get('department', None)
        patient = self.request.query_params.get('patient', None)

        if status:
            queryset = queryset.filter(status=status)
        if department:
            queryset = queryset.filter(department_id=department)
        if patient:
            queryset = queryset.filter(patient_id=patient)

        return queryset.order_by('-priority', 'enter_time')

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """更新队列状态"""
        queue = self.get_object()
        status = request.data.get('status')
        if status not in [s[0] for s in Queue.STATUS_CHOICES]:
            return Response({'error': '无效的状态'}, status=400)
        
        queue.update_status(status)
        return Response(QueueSerializer(queue).data)

    @action(detail=False, methods=['get'])
    def search(self, request):
        """搜索队列"""
        query = request.query_params.get('q', '')
        if not query:
            return Response(
                {'error': 'Query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        queues = Queue.objects.filter(
            Q(queue_number__icontains=query) |
            Q(patient__name__icontains=query) |
            Q(patient__id_number__icontains=query) |
            Q(patient__medical_record_number__icontains=query)
        ).order_by('-created_at')

        serializer = self.get_serializer(queues, many=True)
        return Response(serializer.data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """通知模板视图集"""
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get_queryset(self):
        """根据查询参数过滤模板"""
        queryset = NotificationTemplate.objects.all()
        
        # 按代码搜索
        code = self.request.query_params.get('code', None)
        if code:
            queryset = queryset.filter(code__icontains=code)
        
        # 按通知渠道过滤
        channel = self.request.query_params.get('channel', None)
        if channel:
            queryset = queryset.filter(channel_types__contains=[channel])
        
        # 按状态过滤
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)
        
        return queryset

    @action(detail=True, methods=['post'])
    def test_render(self, request, pk=None):
        """测试渲染模板"""
        template = self.get_object()
        context = request.data.get('context', {})
        
        try:
            result = template.render(context)
            return Response(result)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """切换模板状态"""
        template = self.get_object()
        template.is_active = not template.is_active
        template.save()
        
        return Response({
            'status': 'success',
            'is_active': template.is_active
        })


# 添加一个新的视图，用于显示添加队列表单
class AddQueueView(TemplateView):
    """添加队列视图"""
    template_name = 'navigation/add_queue.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 获取活跃的患者、科室和检查项目
        patients = Patient.objects.all()
        departments = Department.objects.filter(is_active=True)
        
        context.update({
            'patients': patients,
            'departments': departments,
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """处理表单提交"""
        try:
            # 获取表单数据
            patient_id = request.POST.get('patient')
            department_id = request.POST.get('department')
            examination_id = request.POST.get('examination')
            equipment_id = request.POST.get('equipment')
            priority = int(request.POST.get('priority', 0))
            notes = request.POST.get('notes', '')
            
            # 验证必填字段
            if not all([patient_id, department_id, examination_id]):
                messages.error(request, '请填写所有必填字段')
                return self.get(request, *args, **kwargs)
            
            # 获取相关对象
            patient = Patient.objects.get(id=patient_id)
            department = Department.objects.get(id=department_id)
            examination = Examination.objects.get(id=examination_id)
            equipment = None
            if equipment_id:
                equipment = Equipment.objects.get(id=equipment_id)
            
            # 验证检查项目是否属于选择的科室
            if examination.department != department:
                messages.error(request, '所选检查项目不属于所选科室')
                return self.get(request, *args, **kwargs)
            
            # 验证设备是否属于选择的科室
            if equipment and equipment.department != department:
                messages.error(request, '所选设备不属于所选科室')
                return self.get(request, *args, **kwargs)
            
            # 创建队列
            queue = Queue(
                patient=patient,
                department=department,
                examination=examination,
                equipment=equipment,
                priority=priority,
                notes=notes,
                status='waiting'
            )
            
            # 计算预计等待时间
            queue.estimated_wait_time = queue.estimate_initial_wait_time()
            
            # 保存队列
            queue.save()
            
            messages.success(request, f'已成功添加患者 {patient.name} 到 {department.name} 的队列')
            
            # 重定向到队列详情页面
            return HttpResponseRedirect(reverse('navigation:queue_info', args=[department.code]))
            
        except Patient.DoesNotExist:
            messages.error(request, '所选患者不存在')
        except Department.DoesNotExist:
            messages.error(request, '所选科室不存在')
        except Examination.DoesNotExist:
            messages.error(request, '所选检查项目不存在')
        except Equipment.DoesNotExist:
            messages.error(request, '所选设备不存在')
        except Exception as e:
            messages.error(request, f'添加队列失败: {str(e)}')
        
        # 如果发生错误，返回表单页面
        return self.get(request, *args, **kwargs)


# API视图
def department_examinations(request, department_id):
    """获取科室下的检查项目"""
    try:
        department = Department.objects.get(id=department_id)
        examinations = Examination.objects.filter(department=department, is_active=True)
        
        # 构建简单的响应数据
        data = [
            {
                'id': exam.id,
                'name': exam.name,
                'code': exam.code,
                'duration': exam.duration,
                'price': str(exam.price)
            }
            for exam in examinations
        ]
        
        return JsonResponse(data, safe=False)
    except Department.DoesNotExist:
        return JsonResponse({'error': '科室不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def department_equipment(request, department_id):
    """获取科室下的设备"""
    try:
        department = Department.objects.get(id=department_id)
        equipment = Equipment.objects.filter(department=department)
        
        # 构建简单的响应数据
        data = [
            {
                'id': eq.id,
                'name': eq.name,
                'code': eq.code,
                'status': eq.status,
                'model': eq.model,
                'location': eq.location
            }
            for eq in equipment
        ]
        
        return JsonResponse(data, safe=False)
    except Department.DoesNotExist:
        return JsonResponse({'error': '科室不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def examination_equipment(request, examination_id):
    """获取检查项目可用的设备"""
    try:
        examination = Examination.objects.get(id=examination_id)
        # 只获取状态为'available'的设备
        equipment = examination.equipment_type.filter(status='available')
        
        # 构建简单的响应数据
        data = [
            {
                'id': eq.id,
                'name': eq.name,
                'code': eq.code,
                'status': eq.status,
                'model': eq.model,
                'location': eq.location,
                'department': {
                    'id': eq.department.id,
                    'name': eq.department.name
                }
            }
            for eq in equipment
        ]
        
        return JsonResponse(data, safe=False)
    except Examination.DoesNotExist:
        return JsonResponse({'error': '检查项目不存在'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
