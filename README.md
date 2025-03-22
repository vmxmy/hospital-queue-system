# 医院检验智能排队引导系统

## 项目概述

医院检验智能排队引导系统是一个专为医疗机构设计的智能化排队管理解决方案。该系统通过人工智能算法优化患者检验流程，提高医疗资源利用效率，减少患者等待时间，提升就医体验。

## 主要功能

### 1. 智能排队管理
- **实时队列监控**：动态显示各检验科室当前排队情况
- **智能分流机制**：根据患者类型、检验项目和设备负载自动分配最优队列
- **优先级管理**：支持紧急检验、老人儿童等特殊人群优先

### 2. 预测分析
- **等待时间预测**：基于历史数据和机器学习模型预测患者等待时间
- **高峰期预测**：分析历史数据预测未来就诊高峰
- **设备利用率分析**：实时监控设备使用情况，优化资源分配

### 3. 通知与引导
- **自动通知**：通过短信、APP提醒患者临近叫号
- **智能导航**：为患者提供个性化导航路线
- **叫号提醒**：多渠道提醒患者，减少过号情况

### 4. 管理功能
- **医护工作台**：医护人员专用界面，便于管理队列和患者
- **数据分析仪表盘**：展示检验效率、等待时间等关键指标
- **异常情况处理**：支持设备故障、紧急加号等异常情况处理

### 5. 集成能力
- **医院HIS系统集成**：与医院现有系统无缝对接
- **LIS系统集成**：与检验信息系统对接，自动获取检验结果
- **第三方系统API**：提供开放接口，支持与其他系统集成

## 技术架构

- **后端**：Django/Python
- **前端**：HTML/CSS/JavaScript
- **数据库**：MySQL/PostgreSQL
- **机器学习**：Prophet时间序列预测模型
- **消息队列**：Redis/Celery
- **实时通讯**：WebSocket

## 部署要求

### 系统要求
- Python 3.8+
- Django 3.2+
- Redis 6.0+
- MySQL 5.7+ 或 PostgreSQL 12+

### 安装步骤

1. 克隆仓库
```bash
git clone https://github.com/vmxmy/hospital-queue-system.git
cd hospital-queue-system
```

2. 创建虚拟环境
```bash
conda env create -f environment.yml
conda activate hospitalLane
```

3. 数据库迁移
```bash
python manage.py migrate
```

4. 启动服务
```bash
./start_django.sh  # 启动Django服务
./start_celery.sh  # 启动Celery worker和beat服务
```

## 系统截图

[此处可添加系统界面截图]

## 贡献指南

欢迎对本项目提出改进建议或直接贡献代码。请遵循以下步骤：

1. Fork本仓库
2. 创建您的特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m '添加了某某功能'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启一个Pull Request

## 许可证

[待定]

## 联系方式

[待补充]

## 致谢

感谢所有为本项目做出贡献的开发者和使用本系统的医疗机构。 