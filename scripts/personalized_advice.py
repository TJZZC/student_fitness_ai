import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
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
# 2. 如果分项标签不存在，报错
# =========================
required_cols = ["CardioLabel", "SpeedLabel", "StrengthLabel"]
for col in required_cols:
    if col not in df.columns:
        raise ValueError(f"缺少列：{col}。请先运行 scripts/add_sub_labels.py")

# =========================
# 3. 构造时序样本
# =========================
window_size = 3
targets = ["Label", "CardioLabel", "SpeedLabel", "StrengthLabel"]

X = []
y_dict = {t: [] for t in targets}

for student_id, group in df.groupby("StudentID"):
    group = group.sort_values("Date").reset_index(drop=True)

    if len(group) <= window_size:
        continue

    for i in range(len(group) - window_size):
        history = group.iloc[i:i+window_size]
        target = group.iloc[i+window_size]

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

        X.append(features)
        for t in targets:
            y_dict[t].append(target[t])

X = np.array(X)
for t in targets:
    y_dict[t] = np.array(y_dict[t])

if len(X) == 0:
    raise ValueError("样本不足，无法训练。")

# =========================
# 4. 训练4个模型
# =========================
indices = np.arange(len(X))
train_idx, test_idx = train_test_split(indices, test_size=0.2, random_state=42)

X_train = X[train_idx]

models = {}

for t in targets:
    y_train = y_dict[t][train_idx]
    model = RandomForestClassifier(
        n_estimators=120,
        random_state=42,
        max_depth=6
    )
    model.fit(X_train, y_train)
    models[t] = model

# =========================
# 5. 趋势分析函数
# =========================
def analyze_trend(history_df):
    """
    根据最近3次数据分析趋势
    """
    trend = {}

    # 肺活量：越高越好
    lung_diff = history_df.iloc[-1]["LungCapacity"] - history_df.iloc[0]["LungCapacity"]
    if lung_diff > 50:
        trend["CardioTrend"] = "改善"
    elif lung_diff < -50:
        trend["CardioTrend"] = "下降"
    else:
        trend["CardioTrend"] = "稳定"

    # 50米跑：越小越好
    run_diff = history_df.iloc[-1]["Run50m"] - history_df.iloc[0]["Run50m"]
    if run_diff < -0.05:
        trend["SpeedTrend"] = "改善"
    elif run_diff > 0.05:
        trend["SpeedTrend"] = "下降"
    else:
        trend["SpeedTrend"] = "稳定"

    # 跳远：越大越好
    jump_diff = history_df.iloc[-1]["Jump"] - history_df.iloc[0]["Jump"]
    if jump_diff > 3:
        trend["StrengthTrend"] = "改善"
    elif jump_diff < -3:
        trend["StrengthTrend"] = "下降"
    else:
        trend["StrengthTrend"] = "稳定"

    # 综合等级：越小越好
    label_diff = history_df.iloc[-1]["Label"] - history_df.iloc[0]["Label"]
    if label_diff < 0:
        trend["OverallTrend"] = "改善"
    elif label_diff > 0:
        trend["OverallTrend"] = "下降"
    else:
        trend["OverallTrend"] = "稳定"

    return trend

# =========================
# 6. 生成个性化训练建议
# =========================
def generate_personalized_plan(pred_result, trend_result):
    """
    pred_result: 模型预测结果
    trend_result: 趋势分析结果
    """
    label_text = ["优秀", "良好", "中等", "差"]

    advice_lines = []
    weekly_plan = []

    overall = pred_result["Label"]
    cardio = pred_result["CardioLabel"]
    speed = pred_result["SpeedLabel"]
    strength = pred_result["StrengthLabel"]

    advice_lines.append(f"预测下一次综合体质等级：{label_text[overall]}")
    advice_lines.append(
        f"分项预测：心肺{label_text[cardio]}，速度{label_text[speed]}，力量{label_text[strength]}"
    )
    advice_lines.append(
        f"趋势判断：综合{trend_result['OverallTrend']}，心肺{trend_result['CardioTrend']}，速度{trend_result['SpeedTrend']}，力量{trend_result['StrengthTrend']}"
    )

    # 找弱项（数值越大越差）
    weak_items = []
    if cardio >= 2:
        weak_items.append("心肺")
    if speed >= 2:
        weak_items.append("速度")
    if strength >= 2:
        weak_items.append("力量")

    if not weak_items:
        advice_lines.append("整体状态较好，建议保持当前训练节奏，并适当增加综合体能训练。")
        weekly_plan.extend([
            "每周2次耐力跑（15~20分钟）",
            "每周2次短距离加速跑训练",
            "每周2次下肢力量与核心稳定训练"
        ])
    else:
        advice_lines.append("当前重点短板：" + "、".join(weak_items))

        if "心肺" in weak_items:
            advice_lines.append("建议加强有氧耐力训练，提高肺活量与持续运动能力。")
            weekly_plan.extend([
                "每周3次中低强度慢跑，每次15~25分钟",
                "每周1~2次间歇跑（如200米×4组）"
            ])

        if "速度" in weak_items:
            advice_lines.append("建议加强起跑反应、步频和短距离冲刺训练。")
            weekly_plan.extend([
                "每周2次30米~50米加速跑训练",
                "每周2次高抬腿、后蹬跑等跑姿专项练习"
            ])

        if "力量" in weak_items:
            advice_lines.append("建议加强下肢爆发力和核心力量训练。")
            weekly_plan.extend([
                "每周2次跳跃训练（原地纵跳、连续跳）",
                "每周2次深蹲、弓步蹲、平板支撑训练"
            ])

    # 趋势补充
    if trend_result["OverallTrend"] == "下降":
        advice_lines.append("最近整体趋势有下降，建议适当增加训练规律性，并关注恢复和睡眠。")
    elif trend_result["OverallTrend"] == "改善":
        advice_lines.append("最近整体趋势在改善，建议保持训练连续性。")

    return advice_lines, weekly_plan

# =========================
# 7. 对单个学生做预测 + 建议
# =========================
def predict_and_advise(student_id: str):
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

    trend_result = analyze_trend(history)
    advice_lines, weekly_plan = generate_personalized_plan(pred_result, trend_result)

    return {
        "student_id": student_id,
        "pred_result": pred_result,
        "trend_result": trend_result,
        "advice_lines": advice_lines,
        "weekly_plan": weekly_plan
    }, "预测成功"

# =========================
# 8. 示例输出
# =========================
sample_student_id = "001"
result, msg = predict_and_advise(sample_student_id)

if result is None:
    print(msg)
else:
    print(f"\n===== 学生 {result['student_id']} 个性化预测报告 =====")

    print("\n【预测结果】")
    for k, v in result["pred_result"].items():
        print(f"{k}: {v}")

    print("\n【趋势分析】")
    for k, v in result["trend_result"].items():
        print(f"{k}: {v}")

    print("\n【个性化训练建议】")
    for line in result["advice_lines"]:
        print("-", line)

    print("\n【每周训练计划示例】")
    for item in result["weekly_plan"]:
        print("-", item)
