#!/bin/bash

# 确保在项目根目录中执行
cd "$(dirname "$0")"

# 终止已有的Celery进程
pkill -f "celery worker" || true

# 清除日志文件
> celery.log

# 设置Celery环境变量
export PYTHONPATH=$(pwd)
export DJANGO_SETTINGS_MODULE=hospitalLane.settings.local

# 以调试模式启动Celery Worker
echo "启动Celery Worker..."
celery -A hospitalLane worker -l debug --pool=solo > celery.log 2>&1 &

echo "Celery Worker已在后台启动 (PID: $!)"
echo "日志输出到: $(pwd)/celery.log"
