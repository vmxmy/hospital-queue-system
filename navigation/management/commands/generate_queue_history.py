"""
从现有已完成队列生成历史记录的命令
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import logging

from navigation.models import Queue, QueueHistory

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '从现有已完成队列生成历史记录'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='处理过去多少天的队列记录，默认30天'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='每批处理的记录数，默认100条'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅模拟运行，不实际创建记录'
        )

    def handle(self, *args, **options):
        days = options['days']
        batch_size = options['batch_size']
        dry_run = options['dry_run']
        
        # 计算起始时间
        start_date = timezone.now() - timedelta(days=days)
        
        # 获取已完成、已取消或已过号的队列
        completed_queues = Queue.objects.filter(
            status__in=['completed', 'cancelled', 'skipped'],
            updated_at__gte=start_date
        ).order_by('-updated_at')
        
        total_count = completed_queues.count()
        self.stdout.write(self.style.HTTP_INFO(f"找到 {total_count} 条已完成/已取消/已过号的队列记录"))
        
        if dry_run:
            self.stdout.write(self.style.WARNING("这是模拟运行，不会实际创建记录"))
            return
        
        # 分批处理
        processed_count = 0
        success_count = 0
        error_count = 0
        
        with transaction.atomic():
            # 创建批次
            for i in range(0, total_count, batch_size):
                batch = completed_queues[i:i+batch_size]
                self.stdout.write(self.style.HTTP_INFO(f"处理批次 {i//batch_size + 1}/{(total_count + batch_size - 1)//batch_size}..."))
                
                for queue in batch:
                    processed_count += 1
                    
                    # 检查是否已有历史记录
                    if QueueHistory.objects.filter(queue_id=queue.id).exists():
                        self.stdout.write(self.style.WARNING(f"队列 {queue.queue_number} 已有历史记录，跳过"))
                        continue
                    
                    try:
                        QueueHistory.create_from_queue(queue)
                        success_count += 1
                        
                        # 每100条记录输出一次进度
                        if success_count % 100 == 0:
                            self.stdout.write(self.style.SUCCESS(f"已成功处理 {success_count} 条记录"))
                            
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(f"处理队列 {queue.queue_number} 失败: {str(e)}"))
        
        self.stdout.write(self.style.SUCCESS(
            f"处理完成: 总共处理 {processed_count} 条记录，"
            f"成功创建 {success_count} 条历史记录，"
            f"失败 {error_count} 条"
        )) 