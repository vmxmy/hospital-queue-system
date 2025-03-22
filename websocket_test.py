#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
import websockets
import json

async def test_websocket():
    """测试WebSocket连接"""
    uri = "ws://localhost:8000/ws/queue_updates/"
    print(f"尝试连接到 {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("WebSocket连接成功！")
            
            # 发送请求初始数据的消息
            await websocket.send(json.dumps({
                'command': 'get_initial_data'
            }))
            print("已发送初始数据请求")
            
            # 等待接收消息
            response = await websocket.recv()
            data = json.loads(response)
            print(f"收到响应: {data.get('type', 'unknown')}")
            print(f"消息体预览: {str(data)[:100]}...")
            
            # 保持连接一段时间
            for i in range(3):
                await asyncio.sleep(2)
                print(f"等待消息中... ({i+1}/3)")
                
                try:
                    # 设置超时
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    print(f"收到新消息: {data.get('type', 'unknown')}")
                except asyncio.TimeoutError:
                    print("没有收到新消息")
            
            # 发送心跳消息
            await websocket.send(json.dumps({
                'command': 'heartbeat'
            }))
            print("已发送心跳消息")
            
            # 等待心跳响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(response)
                print(f"收到心跳响应: {data}")
            except asyncio.TimeoutError:
                print("没有收到心跳响应")
            
            print("测试完成，关闭连接")
    except Exception as e:
        print(f"连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 