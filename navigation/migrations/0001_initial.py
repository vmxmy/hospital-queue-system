# Generated by Django 5.1.7 on 2025-03-21 09:11

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="NotificationCategory",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, verbose_name="分类名称")),
                (
                    "code",
                    models.CharField(
                        max_length=20, unique=True, verbose_name="分类代码"
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="分类描述")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
            options={
                "verbose_name": "通知模板分类",
                "verbose_name_plural": "通知模板分类",
            },
        ),
        migrations.CreateModel(
            name="Department",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="科室名称")),
                (
                    "code",
                    models.CharField(
                        max_length=20, unique=True, verbose_name="科室代码"
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="科室描述")),
                ("location", models.CharField(max_length=200, verbose_name="位置")),
                ("floor", models.CharField(max_length=20, verbose_name="楼层")),
                ("building", models.CharField(max_length=100, verbose_name="建筑")),
                (
                    "contact_phone",
                    models.CharField(max_length=20, verbose_name="联系电话"),
                ),
                (
                    "operating_hours",
                    models.CharField(
                        help_text="例如: 08:00-17:00",
                        max_length=100,
                        verbose_name="运营时间",
                    ),
                ),
                (
                    "max_daily_patients",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="每日最大接诊量"
                    ),
                ),
                (
                    "average_service_time",
                    models.IntegerField(
                        help_text="用于估算等待时间", verbose_name="平均服务时间(分钟)"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="是否启用"),
                ),
                ("notes", models.TextField(blank=True, verbose_name="备注")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
            ],
            options={
                "verbose_name": "科室",
                "verbose_name_plural": "科室",
                "ordering": ["name"],
                "indexes": [
                    models.Index(fields=["code"], name="navigation__code_013792_idx")
                ],
            },
        ),
        migrations.CreateModel(
            name="Equipment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="设备名称")),
                (
                    "code",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="设备编号"
                    ),
                ),
                ("model", models.CharField(max_length=100, verbose_name="型号")),
                (
                    "manufacturer",
                    models.CharField(max_length=100, verbose_name="制造商"),
                ),
                ("location", models.CharField(max_length=200, verbose_name="具体位置")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("available", "可用"),
                            ("in_use", "使用中"),
                            ("maintenance", "维护中"),
                            ("offline", "离线"),
                        ],
                        default="available",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="设备描述")),
                (
                    "maintenance_period",
                    models.IntegerField(
                        help_text="设备需要定期维护的间隔天数",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="维护周期(天)",
                    ),
                ),
                (
                    "last_maintenance_date",
                    models.DateField(
                        blank=True, null=True, verbose_name="上次维护日期"
                    ),
                ),
                (
                    "next_maintenance_date",
                    models.DateField(
                        blank=True, null=True, verbose_name="下次维护日期"
                    ),
                ),
                (
                    "average_service_time",
                    models.IntegerField(
                        help_text="平均每位患者的检查时间",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="平均检查时间(分钟)",
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="备注")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="navigation.department",
                        verbose_name="所属科室",
                    ),
                ),
            ],
            options={
                "verbose_name": "设备",
                "verbose_name_plural": "设备",
                "ordering": ["department", "name"],
            },
        ),
        migrations.CreateModel(
            name="Examination",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100, verbose_name="项目名称")),
                (
                    "code",
                    models.CharField(
                        max_length=50, unique=True, verbose_name="项目代码"
                    ),
                ),
                ("description", models.TextField(verbose_name="项目描述")),
                (
                    "preparation",
                    models.TextField(
                        help_text="患者需要进行的准备工作", verbose_name="检查准备事项"
                    ),
                ),
                (
                    "contraindications",
                    models.TextField(
                        blank=True,
                        help_text="不适合进行此项检查的情况",
                        verbose_name="禁忌症",
                    ),
                ),
                (
                    "duration",
                    models.IntegerField(
                        help_text="标准情况下完成检查需要的时间",
                        validators=[django.core.validators.MinValueValidator(1)],
                        verbose_name="标准检查时长(分钟)",
                    ),
                ),
                (
                    "price",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="检查费用",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="是否启用"),
                ),
                ("notes", models.TextField(blank=True, verbose_name="备注")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="navigation.department",
                        verbose_name="所属科室",
                    ),
                ),
                (
                    "equipment_type",
                    models.ManyToManyField(
                        help_text="可以进行此项检查的设备列表",
                        to="navigation.equipment",
                        verbose_name="可用设备",
                    ),
                ),
            ],
            options={
                "verbose_name": "检查项目",
                "verbose_name_plural": "检查项目",
                "ordering": ["department", "name"],
            },
        ),
        migrations.CreateModel(
            name="NotificationTemplate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "code",
                    models.CharField(
                        help_text="唯一的模板标识符，如：QUEUE_READY",
                        max_length=50,
                        unique=True,
                        verbose_name="模板代码",
                    ),
                ),
                (
                    "title",
                    models.CharField(
                        help_text="通知的标题", max_length=100, verbose_name="模板标题"
                    ),
                ),
                (
                    "content",
                    models.TextField(
                        help_text="使用 {variable} 格式的占位符，如：您的检查({examination})已经开始",
                        verbose_name="模板内容",
                    ),
                ),
                (
                    "channel_types",
                    models.JSONField(
                        default=list,
                        help_text='可选值：["websocket", "sms", "wechat"]',
                        verbose_name="支持的通知渠道",
                    ),
                ),
                (
                    "sms_template_code",
                    models.CharField(
                        blank=True,
                        help_text="短信服务商的模板代码",
                        max_length=50,
                        verbose_name="短信模板代码",
                    ),
                ),
                (
                    "wechat_template_id",
                    models.CharField(
                        blank=True,
                        help_text="微信公众号的模板消息ID",
                        max_length=50,
                        verbose_name="微信模板ID",
                    ),
                ),
                (
                    "description",
                    models.TextField(
                        blank=True, help_text="模板用途说明", verbose_name="描述"
                    ),
                ),
                (
                    "variables",
                    models.JSONField(
                        default=list,
                        help_text='模板中使用的变量列表，如：["patient_name", "examination"]',
                        verbose_name="变量列表",
                    ),
                ),
                (
                    "priority",
                    models.CharField(
                        choices=[
                            ("high", "高优先级"),
                            ("normal", "普通优先级"),
                            ("low", "低优先级"),
                        ],
                        default="normal",
                        max_length=10,
                        verbose_name="优先级",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="是否启用"),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "category",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="navigation.notificationcategory",
                        verbose_name="模板分类",
                    ),
                ),
            ],
            options={
                "verbose_name": "通知模板",
                "verbose_name_plural": "通知模板",
                "ordering": ["code"],
            },
        ),
        migrations.CreateModel(
            name="NotificationStats",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("channel", models.CharField(max_length=20, verbose_name="通知渠道")),
                ("sent_count", models.IntegerField(default=0, verbose_name="发送次数")),
                (
                    "success_count",
                    models.IntegerField(default=0, verbose_name="成功次数"),
                ),
                ("fail_count", models.IntegerField(default=0, verbose_name="失败次数")),
                ("date", models.DateField(verbose_name="统计日期")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="navigation.notificationtemplate",
                        verbose_name="通知模板",
                    ),
                ),
            ],
            options={
                "verbose_name": "通知统计",
                "verbose_name_plural": "通知统计",
            },
        ),
        migrations.CreateModel(
            name="NotificationTemplateVersion",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("version", models.IntegerField(verbose_name="版本号")),
                ("content", models.TextField(verbose_name="内容")),
                ("title", models.CharField(max_length=100, verbose_name="标题")),
                ("variables", models.JSONField(verbose_name="变量列表")),
                ("channel_types", models.JSONField(verbose_name="通知渠道")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "template",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="versions",
                        to="navigation.notificationtemplate",
                        verbose_name="通知模板",
                    ),
                ),
            ],
            options={
                "verbose_name": "通知模板版本",
                "verbose_name_plural": "通知模板版本",
            },
        ),
        migrations.CreateModel(
            name="Patient",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=50, verbose_name="姓名")),
                (
                    "id_number",
                    models.CharField(
                        max_length=18, unique=True, verbose_name="身份证号"
                    ),
                ),
                (
                    "gender",
                    models.CharField(
                        choices=[("M", "男"), ("F", "女"), ("O", "其他")],
                        max_length=1,
                        verbose_name="性别",
                    ),
                ),
                ("birth_date", models.DateField(verbose_name="出生日期")),
                ("phone", models.CharField(max_length=20, verbose_name="联系电话")),
                (
                    "address",
                    models.CharField(blank=True, max_length=200, verbose_name="地址"),
                ),
                (
                    "medical_record_number",
                    models.CharField(max_length=50, unique=True, verbose_name="病历号"),
                ),
                (
                    "priority",
                    models.IntegerField(
                        choices=[(0, "普通"), (1, "加急"), (2, "特急"), (3, "危急")],
                        default=0,
                        help_text="患者优先级，影响排队顺序",
                        verbose_name="优先级",
                    ),
                ),
                (
                    "special_needs",
                    models.TextField(blank=True, verbose_name="特殊需求"),
                ),
                ("medical_history", models.TextField(blank=True, verbose_name="病史")),
                ("allergies", models.TextField(blank=True, verbose_name="过敏史")),
                ("notes", models.TextField(blank=True, verbose_name="备注")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "user",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="用户账号",
                    ),
                ),
            ],
            options={
                "verbose_name": "患者",
                "verbose_name_plural": "患者",
                "ordering": ["-priority", "created_at"],
            },
        ),
        migrations.CreateModel(
            name="Queue",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "queue_number",
                    models.CharField(
                        editable=False,
                        max_length=20,
                        unique=True,
                        verbose_name="队列号",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("waiting", "等待中"),
                            ("processing", "处理中"),
                            ("completed", "已完成"),
                            ("cancelled", "已取消"),
                            ("skipped", "已过号"),
                        ],
                        default="waiting",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "priority",
                    models.IntegerField(
                        default=0,
                        help_text="队列优先级，继承自患者优先级，可单独调整",
                        verbose_name="优先级",
                    ),
                ),
                (
                    "estimated_wait_time",
                    models.IntegerField(
                        help_text="系统预测的等待时间",
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="预计等待时间(分钟)",
                    ),
                ),
                (
                    "actual_wait_time",
                    models.IntegerField(
                        blank=True, null=True, verbose_name="实际等待时间(分钟)"
                    ),
                ),
                (
                    "enter_time",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="进入队列时间"
                    ),
                ),
                (
                    "start_time",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="开始服务时间"
                    ),
                ),
                (
                    "end_time",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="结束服务时间"
                    ),
                ),
                ("notes", models.TextField(blank=True, verbose_name="备注")),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, verbose_name="创建时间"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="更新时间"),
                ),
                (
                    "department",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="navigation.department",
                        verbose_name="科室",
                    ),
                ),
                (
                    "equipment",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="navigation.equipment",
                        verbose_name="设备",
                    ),
                ),
                (
                    "examination",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="navigation.examination",
                        verbose_name="检查项目",
                    ),
                ),
                (
                    "patient",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="navigation.patient",
                        verbose_name="患者",
                    ),
                ),
            ],
            options={
                "verbose_name": "排队队列",
                "verbose_name_plural": "排队队列",
                "ordering": ["-priority", "enter_time"],
            },
        ),
        migrations.AddIndex(
            model_name="equipment",
            index=models.Index(fields=["code"], name="navigation__code_195892_idx"),
        ),
        migrations.AddIndex(
            model_name="equipment",
            index=models.Index(fields=["status"], name="navigation__status_8a480d_idx"),
        ),
        migrations.AddIndex(
            model_name="examination",
            index=models.Index(fields=["code"], name="navigation__code_c2bf62_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationtemplate",
            index=models.Index(fields=["code"], name="navigation__code_70a0ff_idx"),
        ),
        migrations.AddIndex(
            model_name="notificationstats",
            index=models.Index(
                fields=["template", "date"], name="navigation__templat_7dc207_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="notificationstats",
            index=models.Index(
                fields=["channel", "date"], name="navigation__channel_77baa6_idx"
            ),
        ),
        migrations.AlterUniqueTogether(
            name="notificationstats",
            unique_together={("template", "channel", "date")},
        ),
        migrations.AlterUniqueTogether(
            name="notificationtemplateversion",
            unique_together={("template", "version")},
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(
                fields=["id_number"], name="navigation__id_numb_855a5b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="patient",
            index=models.Index(
                fields=["medical_record_number"], name="navigation__medical_baa490_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="queue",
            index=models.Index(fields=["status"], name="navigation__status_ae9160_idx"),
        ),
        migrations.AddIndex(
            model_name="queue",
            index=models.Index(
                fields=["queue_number"], name="navigation__queue_n_34cabc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="queue",
            index=models.Index(
                fields=["-priority", "enter_time"],
                name="navigation__priorit_31a962_idx",
            ),
        ),
    ]
