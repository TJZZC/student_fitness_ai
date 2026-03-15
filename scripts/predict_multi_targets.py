import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
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
df = df.sort_values(["StudentID", "Date"]).reset_index(drop=True)

# =========================
# 2. 构造时序样本
# 前3次 -> 预测第4次
# =========================
window_size = 3

base_feature_cols = [
    "BMI", "LungCapacity", "Run50m", "Jump",
    "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
]

targets = ["Label", "CardioLabel", "SpeedLabel", "StrengthLabel"]

X = []
y_dict = {t: [] for t in targets}
meta = []

for student_id, group in df.groupby("StudentID"):
    group = group.sort_values("Date").reset_index(drop=True)

    if len(group) <= window_size:
        continue

    for i in range(len(group) - window_size):
        history = group.iloc[i:i+window_size]
        target = group.iloc[i+window_size]

        features = []

        # 历史展开特征
        for _, row in history.iterrows():
            features.extend([
                row["BMI"],
                row["LungCapacity"],
                row["Run50m"],
                row["Jump"],
                row["Label"],
                row["CardioLabel"],
                row["SpeedLabel"],
                row["StrengthLabel"]
            ])

        # 趋势统计特征
        features.extend([
            history["BMI"].mean(),
            history["LungCapacity"].mean(),
            history["Run50m"].mean(),
            history["Jump"].mean(),
            history["Label"].mean(),
            history["CardioLabel"].mean(),
            history["SpeedLabel"].mean(),
            history["StrengthLabel"].mean(),

            history.iloc[-1]["BMI"] - history.iloc[0]["BMI"],
            history.iloc[-1]["LungCapacity"] - history.iloc[0]["LungCapacity"],
            history.iloc[-1]["Run50m"] - history.iloc[0]["Run50m"],
            history.iloc[-1]["Jump"] - history.iloc[0]["Jump"],

            history.iloc[-1]["Label"] - history.iloc[0]["Label"],
            history.iloc[-1]["CardioLabel"] - history.iloc[0]["CardioLabel"],
            history.iloc[-1]["SpeedLabel"] - history.iloc[0]["SpeedLabel"],
            history.iloc[-1]["StrengthLabel"] - history.iloc[0]["StrengthLabel"],
        ])

        X.append(features)

        for t in targets:
            y_dict[t].append(target[t])

        meta.append({
            "StudentID": student_id,
            "TargetDate": target["Date"]
        })

X = np.array(X)
for t in targets:
    y_dict[t] = np.array(y_dict[t])

print("样本数：", len(X))
print("特征维度：", X.shape[1] if len(X) > 0 else 0)

if len(X) == 0:
    raise ValueError("样本不足，无法训练。")

# =========================
# 3. 划分训练测试集
# 同一个随机划分索引，用于多目标对齐
# =========================
indices = np.arange(len(X))
train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)

X_train = X[train_idx]
X_test = X[test_idx]

# =========================
# 4. 分别训练4个模型
# =========================
models = {}
results = {}

for t in targets:
    y_train = y_dict[t][train_idx]
    y_test = y_dict[t][test_idx]

    model = RandomForestClassifier(
        n_estimators=120,
        random_state=42,
        max_depth=6
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    models[t] = model
    results[t] = {
        "acc": accuracy_score(y_test, y_pred),
        "report": classification_report(y_test, y_pred, zero_division=0)
    }

# =========================
# 5. 输出结果
# =========================
for t in targets:
    print(f"\n===== 预测目标：{t} =====")
    print("Accuracy:", round(results[t]["acc"], 4))
    print(results[t]["report"])

# =========================
# 6. 对单个学生做多标签预测
# =========================
def predict_next_multi(student_id: str):
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
            row["Label"],
            row["CardioLabel"],
            row["SpeedLabel"],
            row["StrengthLabel"]
        ])

    features.extend([
        history["BMI"].mean(),
        history["LungCapacity"].mean(),
        history["Run50m"].mean(),
        history["Jump"].mean(),
        history["Label"].mean(),
        history["CardioLabel"].mean(),
        history["SpeedLabel"].mean(),
        history["StrengthLabel"].mean(),

        history.iloc[-1]["BMI"] - history.iloc[0]["BMI"],
        history.iloc[-1]["LungCapacity"] - history.iloc[0]["LungCapacity"],
        history.iloc[-1]["Run50m"] - history.iloc[0]["Run50m"],
        history.iloc[-1]["Jump"] - history.iloc[0]["Jump"],

        history.iloc[-1]["Label"] - history.iloc[0]["Label"],
        history.iloc[-1]["CardioLabel"] - history.iloc[0]["CardioLabel"],
        history.iloc[-1]["SpeedLabel"] - history.iloc[0]["SpeedLabel"],
        history.iloc[-1]["StrengthLabel"] - history.iloc[0]["StrengthLabel"],
    ])

    pred_result = {}
    for t in targets:
        pred_result[t] = int(models[t].predict([features])[0])

    return pred_result, "预测成功"

# 示例
sample_student_id = "001"
pred_result, msg = predict_next_multi(sample_student_id)

if pred_result is None:
    print(msg)
else:
    label_text = ["优秀", "良好", "中等", "差"]

    print(f"\n学生 {sample_student_id} 下一次综合预测：{pred_result['Label']}（{label_text[pred_result['Label']]}）")
    print(f"学生 {sample_student_id} 下一次心肺预测：{pred_result['CardioLabel']}（{label_text[pred_result['CardioLabel']]}）")
    print(f"学生 {sample_student_id} 下一次速度预测：{pred_result['SpeedLabel']}（{label_text[pred_result['SpeedLabel']]}）")
    print(f"学生 {sample_student_id} 下一次力量预测：{pred_result['StrengthLabel']}（{label_text[pred_result['StrengthLabel']]}）")
