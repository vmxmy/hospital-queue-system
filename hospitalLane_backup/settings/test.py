from .base import *

DEBUG = False

ALLOWED_HOSTS = ['test.your-domain.com']

# 使用SQLite进行测试
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',
    }
}

# 使用内存缓存进行测试
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# 使用内存Channel Layer进行测试
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer'
    }
}

# 使用控制台邮件后端
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# 禁用密码哈希以加快测试速度
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Celery测试设置
CELERY_TASK_ALWAYS_EAGER = True  # 同步执行任务
CELERY_TASK_EAGER_PROPAGATES = True

# 测试媒体文件路径
MEDIA_ROOT = os.path.join(BASE_DIR, 'test_media')

# 日志配置
LOGGING['handlers']['file']['filename'] = os.path.join(BASE_DIR, 'logs', 'test.log')
LOGGING['loggers']['django']['level'] = 'WARNING'
LOGGING['loggers']['navigation']['level'] = 'DEBUG' 