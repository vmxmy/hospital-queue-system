# 医院检验智能排队引导系统 API 文档

## 基础信息

- 基础URL: `/api/`
- 认证方式: Token Authentication
- 响应格式: JSON
- 时间格式: ISO 8601 (YYYY-MM-DD HH:mm:ss)

## 1. 患者管理 API

### 1.1 获取患者列表

```
GET /api/patients/
```

**权限要求：** 已认证用户

**查询参数：**
- `page`: 页码（可选）
- `page_size`: 每页数量（可选）
- `search`: 搜索关键词（可选）

**响应示例：**
```json
{
    "count": 100,
    "next": "http://example.com/api/patients/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "patient_id": "P202503001",
            "name": "张三",
            "gender": "M",
            "age": 45,
            "phone": "13800138000",
            "medical_record_number": "MR202503001"
        }
    ]
}
```

**Python 调用示例：**
```python
import requests

def get_patients(token, page=1):
    headers = {'Authorization': f'Token {token}'}
    response = requests.get(
        'http://example.com/api/patients/',
        headers=headers,
        params={'page': page}
    )
    return response.json()
```

### 1.2 创建新患者

```
POST /api/patients/
```

**权限要求：** 已认证用户

**请求体：**
```json
{
    "patient_id": "P202503001",
    "name": "张三",
    "gender": "M",
    "age": 45,
    "phone": "13800138000",
    "medical_record_number": "MR202503001"
}
```

**响应示例：**
```json
{
    "id": 1,
    "patient_id": "P202503001",
    "name": "张三",
    "gender": "M",
    "age": 45,
    "phone": "13800138000",
    "medical_record_number": "MR202503001",
    "created_at": "2025-03-22T12:00:00Z"
}
```

**Python 调用示例：**
```python
def create_patient(token, patient_data):
    headers = {'Authorization': f'Token {token}'}
    response = requests.post(
        'http://example.com/api/patients/',
        headers=headers,
        json=patient_data
    )
    return response.json()
```

### 1.3 获取患者排队记录

```
GET /api/patients/{patient_id}/queues/
```

**权限要求：** 已认证用户

**响应示例：**
```json
{
    "active_queues": [
        {
            "id": 1,
            "queue_number": "A001",
            "status": "waiting",
            "department": "放射科",
            "examination": "CT检查",
            "estimated_wait_time": 15
        }
    ],
    "history_queues": [
        {
            "id": 2,
            "queue_number": "B001",
            "status": "completed",
            "department": "超声科",
            "examination": "腹部超声",
            "actual_wait_time": 20
        }
    ]
}
```

## 2. 科室管理 API

### 2.1 获取科室列表

```
GET /api/departments/
```

**权限要求：** 已认证用户

**响应示例：**
```json
{
    "results": [
        {
            "id": 1,
            "name": "放射科",
            "code": "RAD",
            "description": "提供各类影像学检查",
            "is_active": true,
            "waiting_count": 5
        }
    ]
}
```

### 2.2 获取科室统计信息

```
GET /api/departments/{department_id}/stats/
```

**响应示例：**
```json
{
    "waiting_count": 5,
    "processing_count": 2,
    "avg_wait_time": 15.5,
    "completed_today": 45
}
```

## 3. 队列管理 API

### 3.1 创建新队列

```
POST /api/queues/
```

**请求体：**
```json
{
    "patient_id": 1,
    "department_id": 1,
    "examination_id": 1,
    "priority": 0
}
```

**响应示例：**
```json
{
    "id": 1,
    "queue_number": "A001",
    "status": "waiting",
    "estimated_wait_time": 15,
    "patient": {
        "id": 1,
        "name": "张三"
    },
    "department": {
        "id": 1,
        "name": "放射科"
    }
}
```

### 3.2 更新队列状态

```
POST /api/queues/{queue_id}/update_status/
```

**请求体：**
```json
{
    "status": "processing"
}
```

**响应示例：**
```json
{
    "id": 1,
    "status": "processing",
    "start_time": "2025-03-22T12:30:00Z"
}
```

## 4. 机器学习相关 API

### 4.1 检查模型状态

```
GET /api/ml/model-status/
```

**响应示例：**
```json
{
    "ready": true,
    "departments": ["放射科", "超声科", "心电图室"]
}
```

### 4.2 训练等待时间预测模型

```
POST /api/ml/train-models/
```

**权限要求：** 管理员

**请求体：**
```json
{
    "algorithm": "xgboost"
}
```

**响应示例：**
```json
{
    "status": "success",
    "message": "模型训练任务已启动",
    "task_id": "task-123456"
}
```

### 4.3 更新队列等待时间

```
POST /api/ml/update-queue-wait-time/{queue_id}/
```

**响应示例：**
```json
{
    "status": "success",
    "message": "等待时间已更新",
    "queue_id": 1,
    "estimated_wait_time": 15
}
```

## 5. 通知模板 API

### 5.1 获取通知模板列表

```
GET /api/notification-templates/
```

**权限要求：** 管理员

**响应示例：**
```json
{
    "results": [
        {
            "id": 1,
            "name": "排队提醒",
            "content": "尊敬的{patient_name}，您的{examination}检查预计等待时间为{wait_time}分钟",
            "category": "queue",
            "is_active": true
        }
    ]
}
```

### 5.2 测试模板渲染

```
POST /api/notification-templates/{template_id}/test_render/
```

**请求体：**
```json
{
    "context": {
        "patient_name": "张三",
        "examination": "CT检查",
        "wait_time": 15
    }
}
```

**响应示例：**
```json
{
    "rendered_content": "尊敬的张三，您的CT检查预计等待时间为15分钟"
}
```

## 错误处理

所有 API 在发生错误时会返回适当的 HTTP 状态码和错误信息：

```json
{
    "status": "error",
    "message": "错误描述",
    "code": "ERROR_CODE"
}
```

常见状态码：
- 200: 请求成功
- 201: 创建成功
- 400: 请求参数错误
- 401: 未认证
- 403: 权限不足
- 404: 资源不存在
- 500: 服务器内部错误

## Python SDK 示例

```python
class HospitalQueueAPI:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {'Authorization': f'Token {token}'}
    
    def get_patients(self, page=1):
        response = requests.get(
            f'{self.base_url}/api/patients/',
            headers=self.headers,
            params={'page': page}
        )
        return response.json()
    
    def create_queue(self, patient_id, department_id, examination_id, priority=0):
        data = {
            'patient_id': patient_id,
            'department_id': department_id,
            'examination_id': examination_id,
            'priority': priority
        }
        response = requests.post(
            f'{self.base_url}/api/queues/',
            headers=self.headers,
            json=data
        )
        return response.json()
    
    def update_queue_status(self, queue_id, status):
        response = requests.post(
            f'{self.base_url}/api/queues/{queue_id}/update_status/',
            headers=self.headers,
            json={'status': status}
        )
        return response.json()
    
    def get_department_stats(self, department_id):
        response = requests.get(
            f'{self.base_url}/api/departments/{department_id}/stats/',
            headers=self.headers
        )
        return response.json()

# 使用示例
api = HospitalQueueAPI('http://example.com', 'your-token')

# 获取患者列表
patients = api.get_patients()

# 创建新队列
queue = api.create_queue(
    patient_id=1,
    department_id=1,
    examination_id=1
)

# 更新队列状态
result = api.update_queue_status(queue['id'], 'processing')

# 获取科室统计
stats = api.get_department_stats(1)
```

## 注意事项

1. 所有需要认证的接口都需要在请求头中包含有效的认证 Token
2. 时间相关的字段都使用 ISO 8601 格式
3. 分页接口默认每页返回 20 条记录
4. 对于大量数据的查询，建议使用分页功能
5. 所有的创建和更新操作都会返回完整的对象数据
6. 机器学习相关的 API 可能需要较长处理时间，建议异步处理 