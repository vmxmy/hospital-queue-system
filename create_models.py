#!/usr/bin/env python
import pickle
import os
os.makedirs("navigation/ml/trained_models", exist_ok=True)
for i in [1, 2, 3]:
    with open(f"navigation/ml/trained_models/wait_time_model_{i}.pkl", "wb") as f:
        pickle.dump({"model_type": "dummy", "dept_id": i}, f)
    print(f"创建了模型文件 wait_time_model_{i}.pkl")
