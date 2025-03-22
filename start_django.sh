#!/bin/bash

# 设置项目根目录
PROJECT_DIR="/Users/xumingyang/app/医院检验智能排队引导系统"
LOG_FILE="$PROJECT_DIR/django_server.log"

echo "=== Django服务器启动脚本 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "正在切换到项目目录: $PROJECT_DIR"
cd "$PROJECT_DIR"

# 首先运行清理脚本
echo "运行清理脚本..."
./kill_django.sh

# 检查虚拟环境
if [[ -z "${CONDA_DEFAULT_ENV}" ]]; then
    echo "激活 hospitalLane 环境..."
    source ~/opt/anaconda3/etc/profile.d/conda.sh
    conda activate hospitalLane
fi

# 检查依赖
echo "检查项目依赖..."
pip list | grep -E "Django|channels|redis|celery" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "正在安装必要的依赖..."
    pip install -r requirements.txt
fi

# 检查数据库迁移
echo "检查数据库迁移..."
python manage.py migrate --check > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "需要进行数据库迁移..."
    python manage.py migrate
fi

# 启动Celery Worker（后台运行）
echo "启动Celery Worker..."
celery -A hospital_queue worker -l info --logfile=celery.log --detach

# 启动Django服务器
echo "启动Django服务器..."
echo "服务器日志将被记录到: $LOG_FILE"
echo "访问地址: http://127.0.0.1:8000"
echo "使用 Ctrl+C 停止服务器"
echo "----------------------------------------"

# 启动Django服务器并将输出重定向到日志文件
python manage.py runserver 2>&1 | tee -a "$LOG_FILE" 