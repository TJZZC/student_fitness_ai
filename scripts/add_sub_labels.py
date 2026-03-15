import os
import pandas as pd

# =========================
# 1. 读取原始数据
# =========================
script_dir = os.path.dirname(__file__)
csv_path = os.path.join(script_dir, "../data/students.csv")

if not os.path.exists(csv_path):
    raise FileNotFoundError(f"未找到数据文件：{csv_path}")

df = pd.read_csv(csv_path)

# =========================
# 2. 定义分项标签规则
# 0=优秀 1=良好 2=中等 3=差
# =========================
def cardio_label(lung):
    if lung >= 3500:
        return 0
    elif lung >= 3000:
        return 1
    elif lung >= 2600:
        return 2
    else:
        return 3

def speed_label(run50):
    if run50 <= 7.8:
        return 0
    elif run50 <= 8.5:
        return 1
    elif run50 <= 9.2:
        return 2
    else:
        return 3

def strength_label(jump):
    if jump >= 185:
        return 0
    elif jump >= 170:
        return 1
    elif jump >= 155:
        return 2
    else:
        return 3

# =========================
# 3. 生成新标签
# =========================
df["CardioLabel"] = df["LungCapacity"].apply(cardio_label)
df["SpeedLabel"] = df["Run50m"].apply(speed_label)
df["StrengthLabel"] = df["Jump"].apply(strength_label)

# =========================
# 4. 保存回原文件
# =========================
df.to_csv(csv_path, index=False, encoding="utf-8-sig")

print("已成功写入分项标签：")
print(["CardioLabel", "SpeedLabel", "StrengthLabel"])
print(df.head())
