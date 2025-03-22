"""
测试Prophet模型预测效果的命令行工具
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import logging

from navigation.ml.prophet_predictor import get_prophet_predictor
from navigation.ml.data_collector import QueueDataCollector
from navigation.models import Department, Examination

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '测试Prophet模型的等待时间预测效果'

    def add_arguments(self, parser):
        parser.add_argument(
            '--scope',
            type=str,
            choices=['global', 'department', 'examination'],
            default='global',
            help='指定测试范围: global=全局模型, department=科室模型, examination=检查项目模型'
        )
        parser.add_argument(
            '--id',
            type=int,
            default=None,
            help='指定科室ID或检查项目ID，仅在scope=department或examination时有效'
        )
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='预测未来多少小时的等待时间趋势'
        )
        parser.add_argument(
            '--save',
            action='store_true',
            help='保存预测结果图表'
        )
        parser.add_argument(
            '--queue-count',
            type=int,
            default=None,
            help='模拟当前排队人数，用于调整预测'
        )

    def handle(self, *args, **options):
        scope = options['scope']
        target_id = options['id']
        hours = options['hours']
        save_plot = options['save']
        queue_count = options['queue_count']
        
        # 根据范围获取预测器
        if scope == 'department':
            if not target_id:
                raise CommandError("使用科室范围时必须指定科室ID")
            try:
                dept = Department.objects.get(id=target_id)
                predictor = get_prophet_predictor(department_id=target_id)
                entity_name = f"科室: {dept.name}"
            except Department.DoesNotExist:
                raise CommandError(f"找不到ID为{target_id}的科室")
        elif scope == 'examination':
            if not target_id:
                raise CommandError("使用检查项目范围时必须指定检查项目ID")
            try:
                exam = Examination.objects.get(id=target_id)
                predictor = get_prophet_predictor(examination_id=target_id)
                entity_name = f"检查项目: {exam.name}"
            except Examination.DoesNotExist:
                raise CommandError(f"找不到ID为{target_id}的检查项目")
        else:  # global
            predictor = get_prophet_predictor()
            entity_name = "全局"
        
        # 检查模型是否存在
        if not predictor or not predictor.model:
            self.stdout.write(self.style.ERROR(f"{entity_name}的Prophet模型不存在，请先训练模型"))
            return
        
        # 生成未来数据点用于预测
        future_dates = pd.date_range(
            start=timezone.now(),
            periods=hours,
            freq='H'
        )
        future = pd.DataFrame({'ds': future_dates})
        
        # 预测结果
        try:
            forecast = predictor.model.predict(future)
            
            # 打印预测结果摘要
            self.stdout.write(self.style.HTTP_INFO(f"{entity_name}的等待时间预测结果:"))
            self.stdout.write("时间点\t\t预测等待时间(分钟)\t置信区间")
            
            for idx, row in forecast.iterrows():
                if idx % (max(1, hours // 10)) == 0:  # 只显示一部分结果
                    self.stdout.write(f"{row['ds']}\t{row['yhat']:.1f}\t\t({row['yhat_lower']:.1f} - {row['yhat_upper']:.1f})")
            
            # 如果指定了排队人数，做一次具体预测
            if queue_count is not None:
                adjusted_prediction = predictor.predict(
                    date=timezone.now(),
                    queue_count=queue_count
                )
                
                self.stdout.write(self.style.SUCCESS(
                    f"\n当前排队人数为{queue_count}人时，预计等待时间为: {adjusted_prediction:.1f}分钟"
                ))
            
            # 生成图表
            fig = predictor.model.plot(forecast)
            plt.title(f'{entity_name}等待时间预测趋势')
            plt.xlabel('时间')
            plt.ylabel('等待时间(分钟)')
            
            # 显示组件图
            fig_comp = predictor.model.plot_components(forecast)
            
            # 保存图片
            if save_plot:
                plots_dir = os.path.join('media', 'ml_plots')
                os.makedirs(plots_dir, exist_ok=True)
                
                if scope == 'department':
                    plot_name = f"prophet_dept_{target_id}"
                elif scope == 'examination':
                    plot_name = f"prophet_exam_{target_id}"
                else:
                    plot_name = "prophet_global"
                
                fig_path = os.path.join(plots_dir, f"{plot_name}_forecast.png")
                fig_comp_path = os.path.join(plots_dir, f"{plot_name}_components.png")
                
                fig.savefig(fig_path)
                fig_comp.savefig(fig_comp_path)
                
                self.stdout.write(self.style.SUCCESS(f"预测图表已保存到: {fig_path}"))
                self.stdout.write(self.style.SUCCESS(f"组件图表已保存到: {fig_comp_path}"))
            
            plt.show()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"预测失败: {str(e)}"))
            logger.error(f"Prophet预测失败: {str(e)}", exc_info=True) 