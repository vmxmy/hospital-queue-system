from rest_framework import serializers
from .models.patient import Patient
from .models.department import Department
from .models.equipment import Equipment
from .models.examination import Examination
from .models.queue import Queue
from .models.notification_template import NotificationTemplate
import re


class PatientSerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    current_queue = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'name', 'id_number', 'gender', 'birth_date', 'phone',
            'address', 'medical_record_number', 'priority', 'special_needs',
            'medical_history', 'allergies', 'age', 'current_queue'
        ]
        read_only_fields = ['age', 'current_queue']

    def get_age(self, obj):
        return obj.get_age()

    def get_current_queue(self, obj):
        queue = obj.get_current_queue()
        if queue:
            return QueueSerializer(queue).data
        return None


class DepartmentSerializer(serializers.ModelSerializer):
    current_queue_length = serializers.SerializerMethodField()
    average_wait_time = serializers.SerializerMethodField()
    is_open_now = serializers.SerializerMethodField()

    class Meta:
        model = Department
        fields = [
            'id', 'name', 'code', 'description', 'location', 'floor',
            'building', 'contact_phone', 'operating_hours', 'max_daily_patients',
            'average_service_time', 'is_active', 'current_queue_length',
            'average_wait_time', 'is_open_now'
        ]

    def get_current_queue_length(self, obj):
        return obj.get_current_queue_length()

    def get_average_wait_time(self, obj):
        return obj.get_average_wait_time()

    def get_is_open_now(self, obj):
        return obj.is_open()


class EquipmentSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    needs_maintenance = serializers.SerializerMethodField()

    class Meta:
        model = Equipment
        fields = [
            'id', 'name', 'code', 'model', 'manufacturer', 'department',
            'department_name', 'location', 'status', 'description',
            'maintenance_period', 'last_maintenance_date',
            'next_maintenance_date', 'average_service_time',
            'needs_maintenance'
        ]

    def get_needs_maintenance(self, obj):
        return obj.needs_maintenance()


class ExaminationSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source='department.name', read_only=True)
    available_equipment_count = serializers.SerializerMethodField()
    estimated_wait_time = serializers.SerializerMethodField()

    class Meta:
        model = Examination
        fields = [
            'id', 'name', 'code', 'department', 'department_name',
            'equipment_type', 'description', 'preparation', 'contraindications',
            'duration', 'price', 'is_active', 'available_equipment_count',
            'estimated_wait_time'
        ]

    def get_available_equipment_count(self, obj):
        return obj.get_available_equipment().count()

    def get_estimated_wait_time(self, obj):
        return obj.estimate_wait_time()


class QueueSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.name', read_only=True)
    department_name = serializers.CharField(source='department.name', read_only=True)
    equipment_name = serializers.CharField(source='equipment.name', read_only=True)
    examination_name = serializers.CharField(source='examination.name', read_only=True)
    position = serializers.SerializerMethodField()

    class Meta:
        model = Queue
        fields = [
            'id', 'patient', 'patient_name', 'department', 'department_name',
            'equipment', 'equipment_name', 'examination', 'examination_name',
            'queue_number', 'status', 'priority', 'estimated_wait_time',
            'actual_wait_time', 'enter_time', 'start_time', 'end_time',
            'position', 'notes'
        ]
        read_only_fields = [
            'queue_number', 'actual_wait_time', 'start_time', 'end_time',
            'position'
        ]

    def get_position(self, obj):
        if obj.status == 'waiting':
            return obj.get_position()
        return None


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """通知模板序列化器"""

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'code', 'title', 'content', 'channel_types',
            'sms_template_code', 'wechat_template_id', 'description',
            'variables', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def validate_channel_types(self, value):
        """验证通知渠道"""
        valid_channels = {
            channel[0] for channel in NotificationTemplate.CHANNEL_CHOICES
        }
        invalid_channels = set(value) - valid_channels
        if invalid_channels:
            raise serializers.ValidationError(
                f'无效的通知渠道：{", ".join(invalid_channels)}'
            )
        return value

    def validate(self, data):
        """验证模板数据"""
        # 验证模板变量
        if 'content' in data and 'variables' in data:
            template_vars = set(re.findall(r'\{(\w+)\}', data['content']))
            declared_vars = set(data['variables'])
            
            # 检查是否所有使用的变量都在变量列表中声明
            undeclared_vars = template_vars - declared_vars
            if undeclared_vars:
                raise serializers.ValidationError({
                    'variables': f'模板中使用的变量未在变量列表中声明：{", ".join(undeclared_vars)}'
                })
            
            # 检查是否所有声明的变量都在模板中使用
            unused_vars = declared_vars - template_vars
            if unused_vars:
                raise serializers.ValidationError({
                    'variables': f'变量列表中的变量未在模板中使用：{", ".join(unused_vars)}'
                })
        
        # 验证短信模板代码
        if ('channel_types' in data and 
            'sms' in data['channel_types'] and 
            not data.get('sms_template_code')):
            raise serializers.ValidationError({
                'sms_template_code': '启用短信通知时必须提供短信模板代码'
            })
        
        # 验证微信模板ID
        if ('channel_types' in data and 
            'wechat' in data['channel_types'] and 
            not data.get('wechat_template_id')):
            raise serializers.ValidationError({
                'wechat_template_id': '启用微信通知时必须提供微信模板ID'
            })
        
        return data 