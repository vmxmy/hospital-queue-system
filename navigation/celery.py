app.conf.beat_schedule = {
    # 其他定时任务...
    
    # 添加机器学习模型训练定时任务（每周一次）
    'train-wait-time-models-weekly': {
        'task': 'navigation.ml.tasks.train_wait_time_models',
        'schedule': crontab(hour=2, minute=0, day_of_week=1),  # 每周一凌晨2点
        'args': (),
        'kwargs': {'algorithm': 'xgboost'},  # 默认使用XGBoost算法
    },
    
    # 定期更新所有等待中队列的预测等待时间（每5分钟一次）
    'update-predicted-wait-times': {
        'task': 'navigation.ml.tasks.update_predicted_wait_times',
        'schedule': 300.0,  # 每5分钟
        'args': (),
    },
} 