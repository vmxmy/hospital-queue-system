import os
import django
import numpy as np
import pandas as pd
from collections import Counter
from django.db.models import Count

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hospitalLane.settings')
django.setup()

# 导入模型
from navigation.models import QueueHistory, Department, Examination

# 获取所有等待时间数据
wait_times = list(QueueHistory.objects.values_list('actual_wait_time', flat=True))

# 基本统计信息
print(f"样本总数: {len(wait_times)}")
print(f"最小值: {min(wait_times)}")
print(f"最大值: {max(wait_times)}")
print(f"平均值: {np.mean(wait_times):.2f}")
print(f"中位数: {np.median(wait_times)}")
print(f"标准差: {np.std(wait_times):.2f}")
print("\n")

# 按区间统计分布
bins = range(0, 301, 20)
labels = [f"{i}-{i+19}" for i in bins]
bins_count = {}

for i, label in enumerate(labels):
    if i < len(bins) - 1:
        start = bins[i]
        end = bins[i+1]
        count = len([t for t in wait_times if start <= t < end])
        bins_count[label] = count

print("等待时间分布(分钟):")
for label, count in sorted(bins_count.items()):
    percentage = (count / len(wait_times)) * 100
    print(f"{label}: {count} ({percentage:.2f}%)")
print("\n")

# 按科室统计等待时间
print("各科室等待时间统计:")
departments = Department.objects.all()

for dept in departments:
    dept_wait_times = list(QueueHistory.objects.filter(department=dept).values_list('actual_wait_time', flat=True))
    if dept_wait_times:
        print(f"\n{dept.name} (记录数: {len(dept_wait_times)})")
        print(f"  最小值: {min(dept_wait_times)}")
        print(f"  最大值: {max(dept_wait_times)}")
        print(f"  平均值: {np.mean(dept_wait_times):.2f}")
        print(f"  中位数: {np.median(dept_wait_times)}")
        print(f"  标准差: {np.std(dept_wait_times):.2f}")

# 按检查项目统计等待时间
print("\n\n按检查项目统计等待时间:")
# 获取前15个最常见的检查项目
popular_examinations = QueueHistory.objects.values('examination').annotate(
    count=Count('id')).order_by('-count')[:15]
popular_exam_ids = [item['examination'] for item in popular_examinations]
examinations = Examination.objects.filter(id__in=popular_exam_ids)

for exam in examinations:
    exam_wait_times = list(QueueHistory.objects.filter(examination=exam).values_list('actual_wait_time', flat=True))
    if exam_wait_times:
        count = len(exam_wait_times)
        print(f"\n{exam.name} ({exam.department.name}, 记录数: {count})")
        print(f"  最小值: {min(exam_wait_times)}")
        print(f"  最大值: {max(exam_wait_times)}")
        print(f"  平均值: {np.mean(exam_wait_times):.2f}")
        print(f"  中位数: {np.median(exam_wait_times)}")
        print(f"  标准差: {np.std(exam_wait_times):.2f}")
        print(f"  检查时长: {exam.duration}分钟")

# 按优先级统计等待时间
print("\n\n按优先级统计等待时间:")
priorities = QueueHistory.objects.values_list('priority', flat=True).distinct()

for priority in sorted(priorities):
    priority_wait_times = list(QueueHistory.objects.filter(priority=priority).values_list('actual_wait_time', flat=True))
    if priority_wait_times:
        print(f"\n优先级 {priority} (记录数: {len(priority_wait_times)})")
        print(f"  最小值: {min(priority_wait_times)}")
        print(f"  最大值: {max(priority_wait_times)}")
        print(f"  平均值: {np.mean(priority_wait_times):.2f}")
        print(f"  中位数: {np.median(priority_wait_times)}")
        print(f"  标准差: {np.std(priority_wait_times):.2f}") 