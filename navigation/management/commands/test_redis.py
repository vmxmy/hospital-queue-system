import json
from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.conf import settings
import redis
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

class Command(BaseCommand):
    help = '测试Redis连接和功能'

    def handle(self, *args, **options):
        self.stdout.write('开始测试Redis连接...\n')
        
        # 测试缓存
        self.test_cache()
        
        # 测试直接Redis连接
        self.test_redis()
        
        # 测试Channels
        self.test_channels()
        
        self.stdout.write(self.style.SUCCESS('所有测试完成！\n'))

    def test_cache(self):
        try:
            self.stdout.write('测试Django缓存...')
            cache.set('test_key', 'test_value', 30)
            value = cache.get('test_key')
            if value == 'test_value':
                self.stdout.write(self.style.SUCCESS('缓存测试成功！\n'))
            else:
                self.stdout.write(self.style.ERROR('缓存测试失败：无法获取存储的值\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'缓存测试出错：{str(e)}\n'))

    def test_redis(self):
        try:
            self.stdout.write('测试直接Redis连接...')
            redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD,
                db=0
            )
            redis_client.set('test_direct_key', 'test_direct_value')
            value = redis_client.get('test_direct_key')
            if value.decode() == 'test_direct_value':
                self.stdout.write(self.style.SUCCESS('直接Redis连接测试成功！\n'))
            else:
                self.stdout.write(self.style.ERROR('直接Redis连接测试失败：无法获取存储的值\n'))
            redis_client.close()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'直接Redis连接测试出错：{str(e)}\n'))

    def test_channels(self):
        try:
            self.stdout.write('测试Channels层...')
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_add)('test_group', 'test_channel')
            async_to_sync(channel_layer.group_send)(
                'test_group',
                {
                    'type': 'test.message',
                    'message': 'test_message'
                }
            )
            self.stdout.write(self.style.SUCCESS('Channels层测试成功！\n'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Channels层测试出错：{str(e)}\n')) 