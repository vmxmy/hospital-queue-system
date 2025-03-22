"""
手动训练Prophet模型的命令行工具
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from navigation.ml.tasks import train_prophet_models, train_global_model, train_department_models, train_examination_models
from navigation.ml.data_collector import QueueDataCollector
from navigation.models import Department, Examination
import logging
import time

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '训练Prophet模型预测等待时间'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scope',
            type=str,
            choices=['all', 'global', 'department', 'examination'],
            default='all',
            help='指定训练范围: all=全部, global=全局模型, department=科室模型, examination=检查项目模型'
        )
        parser.add_argument(
            '--id',
            type=int,
            default=None,
            help='指定科室ID或检查项目ID，仅在scope=department或examination时有效'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='使用过去多少天的数据进行训练，默认30天'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新训练，即使已有模型'
        )

    def handle(self, *args, **options):
        start_time = time.time()
        scope = options['scope']
        target_id = options['id']
        days = options['days']
        force = options['force']
        
        self.stdout.write(self.style.HTTP_INFO(f"开始训练Prophet模型 (范围: {scope})..."))
        
        # 创建数据收集器
        collector = QueueDataCollector(days_lookback=days)
        
        if scope == 'all':
            # 训练所有模型 - 直接调用函数而不是异步任务
            self.stdout.write(self.style.HTTP_INFO("开始训练所有模型..."))
            result = train_prophet_models()
            if result.get("status") == "success":
                self.stdout.write(self.style.SUCCESS("所有模型训练成功"))
            else:
                self.stdout.write(self.style.ERROR(f"模型训练出错: {result.get('message')}"))
            
        elif scope == 'global':
            # 训练全局模型
            success = train_global_model(collector)
            if success:
                self.stdout.write(self.style.SUCCESS("全局模型训练成功"))
            else:
                self.stdout.write(self.style.ERROR("全局模型训练失败，请检查日志获取详细信息"))
                
        elif scope == 'department':
            # 训练科室模型
            if target_id:
                try:
                    # 训练指定科室模型
                    dept = Department.objects.get(id=target_id)
                    self.stdout.write(self.style.HTTP_INFO(f"训练科室'{dept.name}'的模型..."))
                    
                    # 准备科室数据
                    dept_data = collector.prepare_prophet_data(department_id=dept.id)
                    
                    if dept_data.empty:
                        self.stdout.write(self.style.WARNING(f"科室'{dept.name}'没有足够的历史数据用于训练"))
                        return
                    
                    # 获取科室预测器
                    from navigation.ml.prophet_predictor import get_prophet_predictor
                    predictor = get_prophet_predictor(department_id=dept.id)
                    
                    # 训练模型
                    success = predictor.train(dept_data)
                    
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"科室'{dept.name}'模型训练成功"))
                    else:
                        self.stdout.write(self.style.ERROR(f"科室'{dept.name}'模型训练失败"))
                    
                except Department.DoesNotExist:
                    raise CommandError(f"找不到ID为{target_id}的科室")
            else:
                # 训练所有科室模型
                success = train_department_models(collector)
                if success:
                    self.stdout.write(self.style.SUCCESS("所有科室模型训练完成"))
                else:
                    self.stdout.write(self.style.ERROR("科室模型训练失败，请检查日志获取详细信息"))
        
        elif scope == 'examination':
            # 训练检查项目模型
            if target_id:
                try:
                    # 训练指定检查项目模型
                    exam = Examination.objects.get(id=target_id)
                    self.stdout.write(self.style.HTTP_INFO(f"训练检查项目'{exam.name}'的模型..."))
                    
                    # 准备检查项目数据
                    exam_data = collector.prepare_prophet_data(examination_id=exam.id)
                    
                    if exam_data.empty:
                        self.stdout.write(self.style.WARNING(f"检查项目'{exam.name}'没有足够的历史数据用于训练"))
                        return
                    
                    # 获取检查项目预测器
                    from navigation.ml.prophet_predictor import get_prophet_predictor
                    predictor = get_prophet_predictor(examination_id=exam.id)
                    
                    # 训练模型
                    success = predictor.train(exam_data)
                    
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"检查项目'{exam.name}'模型训练成功"))
                    else:
                        self.stdout.write(self.style.ERROR(f"检查项目'{exam.name}'模型训练失败"))
                    
                except Examination.DoesNotExist:
                    raise CommandError(f"找不到ID为{target_id}的检查项目")
            else:
                # 训练所有检查项目模型
                success = train_examination_models(collector)
                if success:
                    self.stdout.write(self.style.SUCCESS("所有检查项目模型训练完成"))
                else:
                    self.stdout.write(self.style.ERROR("检查项目模型训练失败，请检查日志获取详细信息"))
        
        elapsed_time = time.time() - start_time
        self.stdout.write(self.style.SUCCESS(f"训练完成，耗时: {elapsed_time:.2f}秒")) 