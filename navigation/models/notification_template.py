from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
import re
import json

User = get_user_model()

class NotificationCategory(models.Model):
    name = models.CharField(max_length=50, verbose_name='分类名称')
    code = models.CharField(max_length=20, unique=True, verbose_name='分类代码')
    description = models.TextField(blank=True, verbose_name='分类描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '通知模板分类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

class NotificationTemplate(models.Model):
    """通知模板模型"""

    CHANNEL_CHOICES = [
        ('websocket', 'WebSocket'),
        ('sms', '短信'),
        ('wechat', '微信'),
    ]

    PRIORITY_CHOICES = [
        ('high', '高优先级'),
        ('normal', '普通优先级'),
        ('low', '低优先级')
    ]

    category = models.ForeignKey(NotificationCategory, on_delete=models.SET_NULL, null=True, verbose_name='模板分类')
    code = models.CharField(
        '模板代码',
        max_length=50,
        unique=True,
        help_text='唯一的模板标识符，如：QUEUE_READY'
    )
    title = models.CharField(
        '模板标题',
        max_length=100,
        help_text='通知的标题'
    )
    content = models.TextField(
        '模板内容',
        help_text='使用 {variable} 格式的占位符，如：您的检查({examination})已经开始'
    )
    channel_types = models.JSONField(
        '支持的通知渠道',
        default=list,
        help_text='可选值：["websocket", "sms", "wechat"]'
    )
    sms_template_code = models.CharField(
        '短信模板代码',
        max_length=50,
        blank=True,
        help_text='短信服务商的模板代码'
    )
    wechat_template_id = models.CharField(
        '微信模板ID',
        max_length=50,
        blank=True,
        help_text='微信公众号的模板消息ID'
    )
    description = models.TextField(
        '描述',
        blank=True,
        help_text='模板用途说明'
    )
    variables = models.JSONField(
        '变量列表',
        default=list,
        help_text='模板中使用的变量列表，如：["patient_name", "examination"]'
    )
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal', verbose_name='优先级')
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        verbose_name = '通知模板'
        verbose_name_plural = '通知模板'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.code} - {self.title}"

    def clean(self):
        """验证模板数据"""
        super().clean()
        
        # 验证模板代码格式
        if not re.match(r'^[A-Z][A-Z0-9_]*$', self.code):
            raise ValidationError({
                'code': '模板代码必须以大写字母开头，只能包含大写字母、数字和下划线'
            })
        
        # 验证通知渠道
        invalid_channels = set(self.channel_types) - {
            channel[0] for channel in self.CHANNEL_CHOICES
        }
        if invalid_channels:
            raise ValidationError({
                'channel_types': f'无效的通知渠道：{", ".join(invalid_channels)}'
            })
        
        # 验证短信模板代码
        if 'sms' in self.channel_types and not self.sms_template_code:
            raise ValidationError({
                'sms_template_code': '启用短信通知时必须提供短信模板代码'
            })
        
        # 验证微信模板ID
        if 'wechat' in self.channel_types and not self.wechat_template_id:
            raise ValidationError({
                'wechat_template_id': '启用微信通知时必须提供微信模板ID'
            })
        
        # 验证模板变量
        template_vars = set(re.findall(r'\{(\w+)\}', self.content))
        declared_vars = set(self.variables)
        
        # 检查是否所有使用的变量都在变量列表中声明
        undeclared_vars = template_vars - declared_vars
        if undeclared_vars:
            raise ValidationError({
                'variables': f'模板中使用的变量未在变量列表中声明：{", ".join(undeclared_vars)}'
            })
        
        # 检查是否所有声明的变量都在模板中使用
        unused_vars = declared_vars - template_vars
        if unused_vars:
            raise ValidationError({
                'variables': f'变量列表中的变量未在模板中使用：{", ".join(unused_vars)}'
            })

    def render(self, context):
        """
        渲染模板内容
        
        Args:
            context: 包含变量值的字典
            
        Returns:
            dict: 包含渲染后的标题和内容
        """
        try:
            # 验证是否提供了所有必需的变量
            missing_vars = set(self.variables) - set(context.keys())
            if missing_vars:
                raise ValueError(
                    f'缺少必需的变量：{", ".join(missing_vars)}'
                )
            
            # 渲染内容
            content = self.content
            for key, value in context.items():
                content = content.replace(f"{{{key}}}", str(value))
            
            return {
                'title': self.title,
                'content': content,
                'channels': self.channel_types
            }
            
        except Exception as e:
            raise ValueError(f'渲染模板失败：{str(e)}')

class NotificationTemplateVersion(models.Model):
    template = models.ForeignKey(NotificationTemplate, on_delete=models.CASCADE, related_name='versions', verbose_name='通知模板')
    version = models.IntegerField(verbose_name='版本号')
    content = models.TextField(verbose_name='内容')
    title = models.CharField(max_length=100, verbose_name='标题')
    variables = models.JSONField(verbose_name='变量列表')
    channel_types = models.JSONField(verbose_name='通知渠道')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='创建人')

    class Meta:
        verbose_name = '通知模板版本'
        verbose_name_plural = verbose_name
        unique_together = ('template', 'version')

    def __str__(self):
        return f"{self.template.code} - v{self.version}" 