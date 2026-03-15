import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
import joblib

# -------------------------
# 数据路径
# -------------------------
script_dir = os.path.dirname(__file__)
csv_path = os.path.join(script_dir, "../data/students.csv")
model_path = os.path.join(script_dir, "../models/best_next_label_model.pkl")

df = pd.read_csv(csv_path)

# -------------------------
# 使用基础列训练模型
# -------------------------
feature_cols = ["BMI", "LungCapacity", "Run50m", "Jump",
                "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"]

X = df[feature_cols]
y = df["Label"]  # 预测综合体质等级

# 划分训练/测试集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 随机森林模型
clf = RandomForestClassifier(n_estimators=120, max_depth=6, random_state=42)
clf.fit(X_train, y_train)

# 保存模型
os.makedirs(os.path.join(script_dir, "../models"), exist_ok=True)
joblib.dump(clf, model_path)
print(f"训练完成，模型已保存：{model_path}")

# 输出训练精度
accuracy = clf.score(X_test, y_test)
print(f"测试集准确率: {accuracy:.4f}")
