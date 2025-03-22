import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer, AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from .models import Patient, Department, Queue
from .utils.notifications import get_notifications


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """通知 WebSocket 消费者"""

    async def connect(self):
        """处理连接请求"""
        user = self.scope["user"]
        
        # 验证用户身份
        if not user.is_authenticated:
            await self.close()
            return
        
        # 获取用户角色和关联对象
        self.user_type = None
        self.related_object = None
        
        try:
            # 检查是否是患者
            patient = await database_sync_to_async(
                lambda: Patient.objects.filter(user=user).first()
            )()
            if patient:
                self.user_type = 'patient'
                self.related_object = patient
            
            # 检查是否是科室工作人员
            department = await database_sync_to_async(
                lambda: Department.objects.filter(staff=user).first()
            )()
            if department:
                self.user_type = 'staff'
                self.related_object = department
            
            if not self.user_type:
                await self.close()
                return
            
            # 添加到对应的通知组
            await self.channel_layer.group_add(
                f"{self.user_type}_{self.related_object.id}",
                self.channel_name
            )
            
            # 接受连接
            await self.accept()
            
            # 发送历史通知
            await self.send_history_notifications()
            
        except Exception as e:
            print(f"Error in connect: {str(e)}")
            await self.close()

    async def disconnect(self, close_code):
        """处理断开连接"""
        if hasattr(self, 'user_type') and hasattr(self, 'related_object'):
            await self.channel_layer.group_discard(
                f"{self.user_type}_{self.related_object.id}",
                self.channel_name
            )

    async def receive_json(self, content):
        """处理接收到的消息"""
        message_type = content.get('type')
        
        if message_type == 'mark_read':
            # 标记通知为已读
            notification_ids = content.get('notification_ids', [])
            await self.mark_notifications_read(notification_ids)
        
        elif message_type == 'heartbeat':
            # 响应心跳检测
            await self.send_json({
                'type': 'heartbeat_response',
                'timestamp': timezone.now().isoformat()
            })

    async def notification_message(self, event):
        """处理通知消息"""
        message = event['message']
        await self.send_json({
            'type': 'notification',
            'message': message
        })

    async def send_history_notifications(self):
        """发送历史通知"""
        if self.related_object:
            notifications = await database_sync_to_async(get_notifications)(
                self.related_object
            )
            if notifications:
                await self.send_json({
                    'type': 'history_notifications',
                    'notifications': notifications
                })

    @database_sync_to_async
    def mark_notifications_read(self, notification_ids):
        """标记通知为已读"""
        if not self.related_object:
            return
        
        cache_key = f'notifications_{self.user_type}_{self.related_object.id}'
        notifications = cache.get(cache_key) or []
        
        updated_notifications = []
        for notification in notifications:
            if notification.get('id') in notification_ids:
                notification['read'] = True
            updated_notifications.append(notification)
        
        cache.set(cache_key, updated_notifications, timeout=86400)


class QueueStatusConsumer(AsyncJsonWebsocketConsumer):
    """队列状态 WebSocket 消费者"""

    async def connect(self):
        """处理连接请求"""
        user = self.scope["user"]
        
        # 验证用户身份
        if not user.is_authenticated:
            await self.close()
            return
        
        # 获取要监听的队列ID
        queue_id = self.scope['url_route']['kwargs'].get('queue_id')
        if not queue_id:
            await self.close()
            return
        
        self.queue_id = queue_id
        
        # 验证访问权限
        if not await self.can_access_queue():
            await self.close()
            return
        
        # 添加到队列状态组
        await self.channel_layer.group_add(
            f"queue_{self.queue_id}",
            self.channel_name
        )
        
        await self.accept()
        
        # 发送当前状态
        await self.send_queue_status()

    async def disconnect(self, close_code):
        """处理断开连接"""
        if hasattr(self, 'queue_id'):
            await self.channel_layer.group_discard(
                f"queue_{self.queue_id}",
                self.channel_name
            )

    async def receive_json(self, content):
        """处理接收到的消息"""
        message_type = content.get('type')
        
        if message_type == 'request_update':
            # 客户端请求更新状态
            await self.send_queue_status()

    async def queue_update(self, event):
        """处理队列更新消息"""
        await self.send_json({
            'type': 'queue_update',
            'data': event['data']
        })

    @database_sync_to_async
    def can_access_queue(self):
        """检查用户是否有权限访问队列"""
        try:
            queue = Queue.objects.get(id=self.queue_id)
            user = self.scope["user"]
            
            # 检查是否是相关患者
            if hasattr(queue.patient, 'user') and queue.patient.user == user:
                return True
            
            # 检查是否是科室工作人员
            if queue.department.staff.filter(id=user.id).exists():
                return True
            
            return False
            
        except Queue.DoesNotExist:
            return False

    @database_sync_to_async
    def get_queue_status(self):
        """获取队列当前状态"""
        try:
            queue = Queue.objects.get(id=self.queue_id)
            return {
                'id': queue.id,
                'status': queue.status,
                'position': queue.get_position(),
                'estimated_wait_time': queue.estimated_wait_time,
                'is_delayed': queue.is_delayed,
                'updated_at': timezone.now().isoformat()
            }
        except Queue.DoesNotExist:
            return None

    async def send_queue_status(self):
        """发送队列状态"""
        status = await self.get_queue_status()
        if status:
            await self.send_json({
                'type': 'queue_status',
                'data': status
            })


class QueueConsumer(AsyncWebsocketConsumer):
    """队列实时更新消费者"""

    async def connect(self):
        """建立连接"""
        try:
            print("WebSocket 连接尝试...")
            
            # 最简单的连接方式 - 直接接受连接，不使用channel_layer
            await self.accept()
            print("WebSocket 连接已接受")

            # 发送连接成功消息
            await self.send(text_data=json.dumps({
                'type': 'connection_established',
                'message': '连接成功'
            }))
            
            # 发送一个简单的测试消息避免数据库错误
            await self.send(text_data=json.dumps({
                'type': 'test_message',
                'message': '这是一个测试消息',
                'timestamp': timezone.now().isoformat()
            }))
        except Exception as e:
            print(f"WebSocket 连接错误: {str(e)}")
            print(f"错误类型: {type(e).__name__}")
            if hasattr(e, '__dict__'):
                print(f"错误详情: {e.__dict__}")
            await self.close(code=1011)

    async def disconnect(self, close_code):
        """断开连接"""
        try:
            print(f"WebSocket 断开连接，代码: {close_code}")
        except Exception as e:
            print(f"断开连接时出错: {str(e)}")
            print(f"错误类型: {type(e).__name__}")

    async def receive(self, text_data):
        """处理接收到的消息"""
        try:
            print(f"收到消息: {text_data}")
            data = json.loads(text_data)
            command = data.get('command')

            # 简化的处理逻辑
            await self.send(text_data=json.dumps({
                'type': 'echo',
                'received': data,
                'timestamp': timezone.now().isoformat()
            }))
            
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': '无效的消息格式'
            }))
        except Exception as e:
            print(f"处理消息时出错: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'处理消息时出错: {str(e)}'
            }))

    async def queue_update(self, event):
        """处理并广播队列更新事件"""
        try:
            print("处理队列更新事件...")
            # 获取最新数据
            stats = await self.get_stats()
            departments = await self.get_departments()
            queues = await self.get_queues()

            # 发送更新
            await self.send(text_data=json.dumps({
                'type': 'queue_update',
                'stats': stats,
                'departments': departments,
                'queues': queues,
                'timestamp': timezone.now().isoformat()
            }))
            print("队列更新数据已发送")
        except Exception as e:
            print(f"更新数据时出错: {str(e)}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'更新数据时出错: {str(e)}'
            }))

    @database_sync_to_async
    def get_stats(self):
        """获取统计数据"""
        try:
            today = timezone.now().date()
            stats = {
                'total_patients': Queue.objects.filter(status__in=['waiting', 'processing']).count(),
                'waiting_queues': Queue.objects.filter(status='waiting').count(),
                'processing_queues': Queue.objects.filter(status='processing').count(),
                'completed_today': Queue.objects.filter(
                    status='completed',
                    completed_time__date=today
                ).count()
            }
            return stats
        except Exception as e:
            print(f"获取统计数据时出错: {str(e)}")
            raise

    @database_sync_to_async
    def get_departments(self):
        """获取科室数据"""
        try:
            departments = []
            for dept in Department.objects.filter(is_active=True).prefetch_related('queue_set'):
                departments.append({
                    'name': dept.name,
                    'code': dept.code,
                    'location': dept.location,
                    'waiting_count': dept.queue_set.filter(status='waiting').count()
                })
            return departments
        except Exception as e:
            print(f"获取科室数据时出错: {str(e)}")
            raise

    @database_sync_to_async
    def get_queues(self):
        """获取队列数据"""
        try:
            queues = []
            for queue in Queue.objects.filter(
                status__in=['waiting', 'processing']
            ).select_related('patient', 'department', 'examination').order_by('enter_time'):
                try:
                    queue_data = {
                        'queue_number': queue.queue_number,
                        'patient_name': queue.patient.name,
                        'department_name': queue.department.name,
                        'examination_name': queue.examination.name,
                        'status': queue.status,
                        'estimated_wait_time': queue.estimated_wait_time,
                        'enter_time': queue.enter_time.isoformat() if queue.enter_time else None
                    }
                    
                    # 计算前面排队的人数
                    if queue.status == 'waiting':
                        try:
                            # 尝试使用ahead_count属性
                            ahead_count = queue.ahead_count
                        except AttributeError:
                            # 如果属性不存在，则直接计算
                            ahead_count = Queue.objects.filter(
                                department=queue.department,
                                status='waiting',
                                enter_time__lt=queue.enter_time
                            ).count()
                        queue_data['ahead_count'] = ahead_count
                    else:
                        queue_data['ahead_count'] = None
                        
                    queues.append(queue_data)
                except Exception as e:
                    print(f"处理单个队列数据时出错: {str(e)}")
                    continue
            return queues
        except Exception as e:
            print(f"获取队列数据时出错: {str(e)}")
            raise 