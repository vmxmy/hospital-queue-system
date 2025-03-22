from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .models import Queue, Patient, Department

@receiver([post_save, post_delete], sender=Queue)
@receiver([post_save, post_delete], sender=Patient)
@receiver([post_save, post_delete], sender=Department)
def trigger_queue_update(sender, instance, **kwargs):
    """
    当队列、患者或科室数据发生变化时触发 WebSocket 更新
    """
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "queue_updates",
        {
            "type": "queue_update",
            "message": "data_updated"
        }
    ) 