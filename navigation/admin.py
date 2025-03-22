from django.contrib import admin
from django.contrib import messages
from django.urls import path, reverse
from django.utils.html import format_html
from django.shortcuts import redirect
from django.http import JsonResponse
from django.template.response import TemplateResponse

from .models import (
    Patient, Department, Equipment, Examination, Queue, QueueHistory,
    NotificationTemplate, NotificationCategory, NotificationStats
)

# 基础管理类
class BaseModelAdmin(admin.ModelAdmin):
    """为所有管理类提供基础配置"""
    list_per_page = 20  # 默认每页显示20条记录
    list_max_show_all = 1000  # 显示全部时最多显示1000条记录
    show_full_result_count = True  # 显示过滤后的记录总数
    
# 自定义管理站点
class NavigationAdminSite(admin.AdminSite):
    site_header = '医院检验智能排队引导系统'
    site_title = '医院检验智能排队引导系统'
    index_title = '管理中心'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('ml/dashboard/', self.admin_view(redirect_to_ml_dashboard), name='ml_dashboard_redirect'),
        ]
        return custom_urls + urls

# 创建自定义管理站点实例
admin_site = NavigationAdminSite(name='navigation_admin')

# 重定向到机器学习模型管理页面
def redirect_to_ml_dashboard(request):
    return redirect(reverse('navigation:admin_ml_dashboard'))

# 患者管理
@admin.register(Patient)
class PatientAdmin(BaseModelAdmin):
    list_display = ('name', 'gender', 'medical_record_number', 'phone', 'birth_date')
    search_fields = ('name', 'medical_record_number', 'phone', 'id_number')
    list_filter = ('gender',)
    list_max_show_all = 2000  # 可以覆盖基类设置

# 科室管理
@admin.register(Department)
class DepartmentAdmin(BaseModelAdmin):
    list_display = ('name', 'code', 'location', 'floor', 'is_active')
    search_fields = ('name', 'code', 'location')
    list_filter = ('is_active',)

# 设备管理
@admin.register(Equipment)
class EquipmentAdmin(BaseModelAdmin):
    list_display = ('name', 'code', 'department', 'status')
    search_fields = ('name', 'code')
    list_filter = ('department', 'status')

# 检查项目管理
@admin.register(Examination)
class ExaminationAdmin(BaseModelAdmin):
    list_display = ('name', 'code', 'department', 'duration', 'price', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('department', 'is_active')

# 队列管理
@admin.register(Queue)
class QueueAdmin(BaseModelAdmin):
    list_display = ('queue_number', 'patient', 'department', 'examination', 'equipment', 'status', 'priority', 
                   'estimated_wait_time', 'actual_wait_time', 'enter_time', 'start_time', 'end_time', 
                   'notes', 'created_at', 'updated_at', 'display_actual_wait_time')
    list_display_links = ('queue_number', 'patient')
    search_fields = ('queue_number', 'patient__name', 'patient__id_number', 'notes')
    list_filter = ('status', 'department', 'priority', 'created_at', 'examination')
    readonly_fields = ('queue_number', 'created_at', 'updated_at')
    actions = ['mark_as_in_progress', 'mark_as_in_service', 'mark_as_completed', 'mark_as_cancelled', 'update_wait_time_with_ml', 'update_wait_time_with_standard']
    list_per_page = 50  # 队列管理页面每页显示50条记录
    list_max_show_all = 5000  # 队列管理页面最多显示5000条记录
    
    fieldsets = (
        ('基本信息', {
            'fields': ('queue_number', 'patient', 'department', 'examination', 'equipment')
        }),
        ('状态信息', {
            'fields': ('status', 'priority')
        }),
        ('时间信息', {
            'fields': ('enter_time', 'start_time', 'end_time', 'created_at', 'updated_at')
        }),
        ('等待时间', {
            'fields': ('estimated_wait_time', 'actual_wait_time')
        }),
        ('其他信息', {
            'fields': ('notes',)
        }),
    )
    
    def display_actual_wait_time(self, obj):
        """显示实际等待时间，如果队列未结束，则显示当前已等待的时间"""
        from django.utils import timezone
        import math
        
        if obj.actual_wait_time is not None:
            return obj.actual_wait_time
        
        if obj.status == 'completed' and obj.start_time and obj.enter_time:
            # 已完成的队列，使用开始服务时间减去进入队列时间
            wait_duration = obj.start_time - obj.enter_time
            return math.floor(wait_duration.total_seconds() / 60)
        elif obj.status == 'waiting' and obj.enter_time:
            # 等待中的队列，使用当前时间减去进入队列时间
            wait_duration = timezone.now() - obj.enter_time
            return math.floor(wait_duration.total_seconds() / 60)
        elif obj.status in ['processing', 'in_service'] and obj.start_time and obj.enter_time:
            # 处理中的队列，使用开始服务时间减去进入队列时间
            wait_duration = obj.start_time - obj.enter_time
            return math.floor(wait_duration.total_seconds() / 60)
        else:
            return '-'
    
    display_actual_wait_time.short_description = '实际等待时间(分钟)'
    
    def mark_as_in_progress(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for queue in queryset:
            if queue.status != 'processing':
                queue.status = 'processing'
                if not queue.start_time:
                    queue.start_time = timezone.now()
                queue.save()
                updated += 1
        self.message_user(request, f"成功将{updated}条记录标记为处理中")
    mark_as_in_progress.short_description = "标记为处理中"
    
    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for queue in queryset:
            if queue.status != 'completed':
                queue.status = 'completed'
                if not queue.end_time:
                    queue.end_time = timezone.now()
                queue.save()
                updated += 1
        self.message_user(request, f"成功将{updated}条记录标记为已完成")
    mark_as_completed.short_description = "标记为已完成"
    
    def mark_as_cancelled(self, request, queryset):
        updated = 0
        for queue in queryset:
            if queue.status != 'cancelled':
                queue.status = 'cancelled'
                queue.save()
                updated += 1
        self.message_user(request, f"成功将{updated}条记录标记为已取消")
    mark_as_cancelled.short_description = "标记为已取消"
    
    def update_wait_time_with_ml(self, request, queryset):
        """使用机器学习模型更新所选队列的预计等待时间"""
        updated = 0
        for queue in queryset:
            if hasattr(queue, 'estimate_initial_wait_time'):
                queue.estimate_initial_wait_time()
                updated += 1
        
        self.message_user(
            request, 
            f'成功使用机器学习模型更新 {updated} 个队列的预计等待时间。',
            messages.SUCCESS
        )
    update_wait_time_with_ml.short_description = "使用机器学习模型更新等待时间"
    
    def update_wait_time_with_standard(self, request, queryset):
        """使用标准算法更新所选队列的预计等待时间"""
        updated = 0
        for queue in queryset:
            if hasattr(queue, 'recalculate_wait_time'):
                queue.recalculate_wait_time()
                updated += 1
        
        self.message_user(
            request, 
            f'成功使用标准算法更新 {updated} 个队列的预计等待时间。',
            messages.SUCCESS
        )
    update_wait_time_with_standard.short_description = "使用标准算法更新等待时间"

    def mark_as_in_service(self, request, queryset):
        from django.utils import timezone
        updated = 0
        for queue in queryset:
            if queue.status != 'in_service':
                queue.status = 'in_service'
                if not queue.start_time:
                    queue.start_time = timezone.now()
                queue.save()
                updated += 1
        self.message_user(request, f"成功将{updated}条记录标记为服务中")
    mark_as_in_service.short_description = "标记为服务中"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add_queue/', self.admin_site.admin_view(self.add_queue_view), name='navigation_queue_add'),
            path('api/department/<int:department_id>/examinations/', self.admin_site.admin_view(self.get_department_examinations), name='api_department_examinations'),
            path('api/department/<int:department_id>/equipment/', self.admin_site.admin_view(self.get_department_equipment), name='api_department_equipment'),
            path('api/examination/<int:examination_id>/equipment/', self.admin_site.admin_view(self.get_examination_equipment), name='api_examination_equipment'),
        ]
        return custom_urls + urls
    
    def add_queue_view(self, request):
        """自定义添加队列视图"""
        # 处理表单提交
        if request.method == 'POST':
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
                    return self.add_queue_view(request)
                
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
                    return self.add_queue_view(request)
                
                # 验证设备是否可用以及是否与检查项目匹配
                if equipment:
                    if equipment.status != 'available':
                        messages.error(request, '所选设备不可用')
                        return self.add_queue_view(request)
                    if equipment not in examination.equipment_type.all():
                        messages.error(request, '所选设备不适用于该检查项目')
                        return self.add_queue_view(request)
                
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
                
                # 重定向到队列列表页面
                return redirect('admin:navigation_queue_changelist')
                
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
        
        # 获取数据并渲染模板
        context = {
            **self.admin_site.each_context(request),
            'title': '添加排队',
            'patients': Patient.objects.all(),
            'departments': Department.objects.filter(is_active=True),
            'opts': self.model._meta,
            'has_change_permission': True,
        }
        return TemplateResponse(request, 'admin/navigation/queue/add_queue.html', context)
    
    def get_department_examinations(self, request, department_id):
        """获取科室下的检查项目API"""
        try:
            department = Department.objects.get(id=department_id)
            examinations = Examination.objects.filter(department=department, is_active=True)
            
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
    
    def get_department_equipment(self, request, department_id):
        """获取科室下的设备API"""
        try:
            department = Department.objects.get(id=department_id)
            equipment_list = Equipment.objects.filter(department=department, status='available')
            
            data = [
                {
                    'id': eq.id,
                    'name': eq.name,
                    'code': eq.code,
                    'status': eq.status
                }
                for eq in equipment_list
            ]
            
            return JsonResponse(data, safe=False)
        except Department.DoesNotExist:
            return JsonResponse({'error': '科室不存在'}, status=404)
    
    def get_examination_equipment(self, request, examination_id):
        """获取检查项目对应的设备API"""
        try:
            examination = Examination.objects.get(id=examination_id)
            # 获取检查项目已关联的可用设备
            equipment_list = examination.equipment_type.filter(status='available')
            
            # 如果没有关联设备，则获取所有该科室的可用设备
            if not equipment_list.exists():
                department = examination.department
                equipment_list = Equipment.objects.filter(
                    department=department,
                    status='available'
                )
            
            data = [
                {
                    'id': eq.id,
                    'name': eq.name,
                    'code': eq.code,
                    'status': eq.status
                }
                for eq in equipment_list
            ]
            
            return JsonResponse(data, safe=False)
        except Examination.DoesNotExist:
            return JsonResponse({'error': '检查项目不存在'}, status=404)
        
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "examination" and request.method == "GET":
            # 如果已经选择了科室，则筛选该科室下的检查项目
            department_id = request.GET.get('department')
            if department_id:
                kwargs["queryset"] = Examination.objects.filter(
                    department_id=department_id,
                    is_active=True
                )
            else:
                kwargs["queryset"] = Examination.objects.filter(is_active=True)
        
        if db_field.name == "equipment" and request.method == "GET":
            # 如果已经选择了检查项目，则筛选该项目可用的设备
            examination_id = request.GET.get('examination')
            department_id = request.GET.get('department')
            
            if examination_id:
                try:
                    examination = Examination.objects.get(id=examination_id)
                    kwargs["queryset"] = examination.equipment_type.filter(status='available')
                except Examination.DoesNotExist:
                    kwargs["queryset"] = Equipment.objects.none()
            elif department_id:
                # 如果只选了科室但没选检查项目，则筛选科室下的设备
                try:
                    kwargs["queryset"] = Equipment.objects.filter(
                        department_id=department_id,
                        status='available'
                    )
                except:
                    kwargs["queryset"] = Equipment.objects.none()
            else:
                kwargs["queryset"] = Equipment.objects.filter(status='available')
                
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    # 添加用于修改表单的JavaScript
    class Media:
        js = (
            'admin/js/vendor/jquery/jquery.min.js',
            'js/queue_admin.js',
        )

# 通知模板分类管理
@admin.register(NotificationCategory)
class NotificationCategoryAdmin(BaseModelAdmin):
    list_display = ('name', 'code', 'description')
    search_fields = ('name', 'code')

# 通知模板管理
@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(BaseModelAdmin):
    list_display = ('code', 'title', 'category', 'priority', 'is_active')
    search_fields = ('code', 'title')
    list_filter = ('category', 'is_active')

# 通知统计管理
@admin.register(NotificationStats)
class NotificationStatsAdmin(BaseModelAdmin):
    list_display = ('template', 'channel', 'date', 'sent_count', 'success_count', 'fail_count')
    list_filter = ('channel', 'date')
    date_hierarchy = 'date'
    list_per_page = 30  # 通知统计页面每页显示30条记录

# 队列历史记录管理
@admin.register(QueueHistory)
class QueueHistoryAdmin(BaseModelAdmin):
    list_display = ('queue_number', 'patient', 'department', 'examination', 'equipment', 'status', 'priority', 
                   'estimated_wait_time', 'actual_wait_time', 'enter_time', 'start_time', 'exit_time', 
                   'notes', 'created_at', 'updated_at')
    list_display_links = ('queue_number', 'patient')
    search_fields = ('queue_number', 'patient__name', 'patient__id_number', 'notes')
    list_filter = ('status', 'department', 'priority', 'created_at', 'examination')
    readonly_fields = ('queue', 'queue_number', 'patient', 'department', 'examination', 'equipment', 
                      'status', 'priority', 'estimated_wait_time', 'actual_wait_time', 
                      'enter_time', 'start_time', 'exit_time', 'created_at', 'updated_at')
    list_per_page = 50
    list_max_show_all = 5000
    
    fieldsets = (
        ('基本信息', {
            'fields': ('queue', 'queue_number', 'patient', 'department', 'examination', 'equipment')
        }),
        ('状态信息', {
            'fields': ('status', 'priority')
        }),
        ('时间信息', {
            'fields': ('enter_time', 'start_time', 'exit_time', 'created_at', 'updated_at')
        }),
        ('等待时间', {
            'fields': ('estimated_wait_time', 'actual_wait_time')
        }),
        ('其他信息', {
            'fields': ('notes',)
        }),
    )
    
    def has_add_permission(self, request):
        """禁止手动添加队列历史记录"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """禁止编辑队列历史记录"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """允许删除队列历史记录"""
        return True

# 在管理站点中注册模型
admin_site.register(Patient, PatientAdmin)
admin_site.register(Department, DepartmentAdmin)
admin_site.register(Equipment, EquipmentAdmin)
admin_site.register(Examination, ExaminationAdmin)
admin_site.register(Queue, QueueAdmin)
admin_site.register(QueueHistory, QueueHistoryAdmin)
admin_site.register(NotificationCategory, NotificationCategoryAdmin)
admin_site.register(NotificationTemplate, NotificationTemplateAdmin)
admin_site.register(NotificationStats, NotificationStatsAdmin)

# 注释掉重复注册的部分
# admin.site.register(Patient, PatientAdmin)
# admin.site.register(Department, DepartmentAdmin)
# admin.site.register(Equipment, EquipmentAdmin)
# admin.site.register(Examination, ExaminationAdmin)
# admin.site.register(Queue, QueueAdmin)
# admin.site.register(NotificationCategory, NotificationCategoryAdmin)
# admin.site.register(NotificationTemplate, NotificationTemplateAdmin)
# admin.site.register(NotificationStats, NotificationStatsAdmin)

# 添加机器学习模型管理入口到管理首页
admin.site.index_template = 'admin/custom_index.html'
