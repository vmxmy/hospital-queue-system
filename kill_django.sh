#!/bin/bash

echo "开始清理Django进程..."

# 查找所有Python运行的Django进程
pids=$(ps aux | grep "python.*manage.py.*runserver" | grep -v grep | awk '{print $2}')

if [ -z "$pids" ]; then
    echo "没有找到运行中的Django进程"
else
    echo "找到以下Django进程ID: $pids"
    for pid in $pids; do
        echo "正在终止进程 $pid..."
        kill -9 $pid
    done
    echo "所有Django进程已终止"
fi

# 检查8000端口
port_pid=$(lsof -ti:8000)
if [ ! -z "$port_pid" ]; then
    echo "发现8000端口被占用，进程ID: $port_pid"
    echo "正在释放8000端口..."
    kill -9 $port_pid
    echo "8000端口已释放"
fi

echo "清理完成！" 