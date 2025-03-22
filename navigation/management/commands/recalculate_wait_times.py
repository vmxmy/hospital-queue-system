from django.core.management.base import BaseCommand
from django.utils import timezone
from navigation.models import Queue


class Command(BaseCommand):
    help = '重新计算所有等待中队列的预计等待时间'

    def add_arguments(self, parser):
        parser.add_argument(
            '--department',
            type=str,
            help='仅重新计算特定科室的队列等待时间，使用科室代码'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='显示详细信息'
        )

    def handle(self, *args, **options):
        start_time = timezone.now()
        verbose = options.get('verbose', False)
        department_code = options.get('department')

        self.stdout.write(self.style.SUCCESS('开始重新计算队列等待时间...'))

        # 获取等待中的队列
        waiting_queues = Queue.objects.filter(status='waiting')
        if department_code:
            waiting_queues = waiting_queues.filter(department__code=department_code)
            self.stdout.write(f'仅处理科室: {department_code}')

        total_count = waiting_queues.count()
        self.stdout.write(f'找到 {total_count} 个等待中的队列')

        # 重新计算每个队列的等待时间
        updated_count = 0
        for i, queue in enumerate(waiting_queues):
            old_wait_time = queue.estimated_wait_time
            try:
                new_wait_time = queue.estimate_initial_wait_time()
                
                if old_wait_time != new_wait_time:
                    queue.estimated_wait_time = new_wait_time
                    queue.save(update_fields=['estimated_wait_time'])
                    updated_count += 1
                    
                    if verbose:
                        self.stdout.write(
                            f'队列 ID:{queue.id} 科室:{queue.department.name} 检查:{queue.examination.name} '
                            f'等待时间从 {old_wait_time} 更新为 {new_wait_time} 分钟'
                        )
                
                # 每10个队列显示一次进度
                if (i + 1) % 10 == 0 or i + 1 == total_count:
                    self.stdout.write(f'处理进度: {i + 1}/{total_count} ({(i + 1) / total_count * 100:.1f}%)')
            
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'处理队列 ID:{queue.id} 时出错: {str(e)}'))

        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(self.style.SUCCESS(
            f'完成! 共更新 {updated_count}/{total_count} 个队列的等待时间，耗时 {duration:.2f} 秒'
        )) 