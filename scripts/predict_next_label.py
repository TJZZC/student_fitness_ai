import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score
from sklearn.model_selection import train_test_split

# =========================
# 1. 读取数据
# =========================
script_dir = os.path.dirname(__file__)
csv_path = os.path.join(script_dir, "../data/students.csv")

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"未找到数据文件：{csv_path}")

df = pd.read_csv(csv_path)
df["Date"] = pd.to_datetime(df["Date"])
df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)

# 按学生、日期排序
df = df.sort_values(["StudentID", "Date"]).reset_index(drop=True)

# =========================
# 2. 构造时序样本
#    用前3次预测下一次Label
# =========================
window_size = 3
feature_cols = ["BMI", "LungCapacity", "Run50m", "Jump", "Label"]

X = []
y = []
meta = []

for student_id, group in df.groupby("StudentID"):
    group = group.sort_values("Date").reset_index(drop=True)

    if len(group) <= window_size:
        continue

    for i in range(len(group) - window_size):
        history = group.iloc[i:i+window_size]
        target = group.iloc[i+window_size]

        features = []

        # 方式1：直接展开最近3次记录
        for _, row in history.iterrows():
            features.extend([
                row["BMI"],
                row["LungCapacity"],
                row["Run50m"],
                row["Jump"],
                row["Label"]
            ])

        # 方式2：增加趋势特征
        features.extend([
            history["BMI"].mean(),
            history["LungCapacity"].mean(),
            history["Run50m"].mean(),
            history["Jump"].mean(),
            history["Label"].mean(),
            history.iloc[-1]["BMI"] - history.iloc[0]["BMI"],
            history.iloc[-1]["LungCapacity"] - history.iloc[0]["LungCapacity"],
            history.iloc[-1]["Run50m"] - history.iloc[0]["Run50m"],
            history.iloc[-1]["Jump"] - history.iloc[0]["Jump"],
            history.iloc[-1]["Label"] - history.iloc[0]["Label"]
        ])

        X.append(features)
        y.append(target["Label"])
        meta.append({
            "StudentID": student_id,
            "TargetDate": target["Date"]
        })

X = np.array(X)
y = np.array(y)

print("样本数：", len(X))
print("特征维度：", X.shape[1] if len(X) > 0 else 0)

if len(X) == 0:
    raise ValueError("样本不足，无法训练。请保证每个学生至少有4条记录。")

# =========================
# 3. 划分训练/测试集
# =========================
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# =========================
# 4. 训练模型
# =========================
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42,
    max_depth=6
)
model.fit(X_train, y_train)

# =========================
# 5. 模型评估
# =========================
y_pred = model.predict(X_test)

print("\n下一次体质等级预测结果：")
print("Accuracy:", round(accuracy_score(y_test, y_pred), 4))
print(classification_report(y_test, y_pred, zero_division=0))

# =========================
# 6. 对某个学生预测下一次等级
# =========================
def predict_next_for_student(student_id: str):
    student_df = df[df["StudentID"] == student_id].sort_values("Date").reset_index(drop=True)

    if len(student_df) < window_size:
        return None, "该学生历史记录不足，无法预测。"

    history = student_df.iloc[-window_size:]

    features = []
    for _, row in history.iterrows():
        features.extend([
            row["BMI"],
            row["LungCapacity"],
            row["Run50m"],
            row["Jump"],
            row["Label"]
        ])

    features.extend([
        history["BMI"].mean(),
        history["LungCapacity"].mean(),
        history["Run50m"].mean(),
        history["Jump"].mean(),
        history["Label"].mean(),
        history.iloc[-1]["BMI"] - history.iloc[0]["BMI"],
        history.iloc[-1]["LungCapacity"] - history.iloc[0]["LungCapacity"],
        history.iloc[-1]["Run50m"] - history.iloc[0]["Run50m"],
        history.iloc[-1]["Jump"] - history.iloc[0]["Jump"],
        history.iloc[-1]["Label"] - history.iloc[0]["Label"]
    ])

    pred = model.predict([features])[0]
    return int(pred), "预测成功"

# 示例
sample_student_id = "001"
pred_label, msg = predict_next_for_student(sample_student_id)

if pred_label is not None:
    label_text = ["优秀", "良好", "中等", "差"][pred_label]
    print(f"\n学生 {sample_student_id} 下一次预测等级：{pred_label}（{label_text}）")
else:
    print(msg)
