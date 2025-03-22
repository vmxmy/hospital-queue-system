from .base import *
import os

DEBUG = False

ALLOWED_HOSTS = ['*']  # 请根据实际情况设置允许的主机名

# Redis配置
REDIS_HOST = '10.10.10.16'
REDIS_PORT = 6379
REDIS_PASSWORD = 'redis_bNQ3S2'
REDIS_URL = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}'

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'hospital_lane',  # 数据库名
        'USER': 'root',
        'PASSWORD': 'mysql_2WshrD',
        'HOST': '10.10.10.16',
        'PORT': '3306',
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

# 安全设置
SECURE_SSL_REDIRECT = False  # 开发环境下关闭SSL重定向
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# 缓存设置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'{REDIS_URL}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': REDIS_PASSWORD,
            'CONNECTION_POOL_CLASS_KWARGS': {
                'max_connections': 100,
                'timeout': 20,
            },
        }
    }
}

# Channels配置
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [f'{REDIS_URL}/0'],
        },
    },
}

# Celery配置
CELERY_BROKER_URL = f'{REDIS_URL}/0'
CELERY_RESULT_BACKEND = f'{REDIS_URL}/0'
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True

# 静态文件设置
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# CORS设置
CORS_ALLOWED_ORIGINS = [
    'https://your-domain.com',
]
CORS_ALLOW_CREDENTIALS = True

# 日志级别设置
LOGGING['loggers']['django']['level'] = 'INFO'
LOGGING['loggers']['navigation']['level'] = 'INFO' 