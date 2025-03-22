import os

# 默认使用本地开发设置
settings_module = os.environ.get('DJANGO_SETTINGS_MODULE', 'hospitalLane.settings.local')

if settings_module == 'hospitalLane.settings.local':
    from .local import *
elif settings_module == 'hospitalLane.settings.prod':
    from .base import *
    from .prod import *
elif settings_module == 'hospitalLane.settings.test':
    from .base import *
    from .test import *
else:
    from .base import * 