import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os

os.makedirs("data", exist_ok=True)

np.random.seed(42)

num_students = 16
records_per_student = 8   # 记录多一点，更适合做时序预测
data = []

def calculate_label(bmi, lung, run50, jump):
    """
    根据指标简单计算综合体质等级
    0=优秀 1=良好 2=中等 3=差
    """
    score = 0

    # BMI（越接近正常越好）
    if 18 <= bmi <= 24:
        score += 3
    elif 16 <= bmi < 18 or 24 < bmi <= 27:
        score += 2
    else:
        score += 1

    # 肺活量（越高越好）
    if lung >= 3500:
        score += 3
    elif lung >= 3000:
        score += 2
    else:
        score += 1

    # 50米跑（越小越好）
    if run50 <= 7.8:
        score += 3
    elif run50 <= 8.8:
        score += 2
    else:
        score += 1

    # 跳远（越大越好）
    if jump >= 185:
        score += 3
    elif jump >= 170:
        score += 2
    else:
        score += 1

    # 总分映射等级
    if score >= 11:
        return 0   # 优秀
    elif score >= 9:
        return 1   # 良好
    elif score >= 7:
        return 2   # 中等
    else:
        return 3   # 差

for sid in range(1, num_students + 1):
    base_date = datetime(2026, 1, 1)

    # 每个学生生成一个“基础水平”
    base_height = np.random.randint(150, 178)
    base_weight = np.random.randint(45, 70)
    base_lung = np.random.randint(2600, 3800)
    base_run50 = np.random.uniform(7.2, 9.5)
    base_jump = np.random.randint(155, 190)

    for i in range(records_per_student):
        date = base_date + timedelta(days=i * 14)  # 每两周一次，更适合看趋势

        # 模拟逐步变化（有些学生变好，有些波动）
        height = base_height
        weight = base_weight + np.random.randint(-2, 3)
        bmi = round(weight / ((height / 100) ** 2), 1)

        lung = int(base_lung + i * np.random.randint(10, 40) + np.random.randint(-60, 60))
        run50 = round(base_run50 - i * np.random.uniform(0.01, 0.05) + np.random.uniform(-0.08, 0.08), 2)
        jump = int(base_jump + i * np.random.randint(1, 4) + np.random.randint(-3, 3))

        label = calculate_label(bmi, lung, run50, jump)

        data.append([
            f"{sid:03}",
            date.strftime("%Y-%m-%d"),
            height,
            weight,
            bmi,
            lung,
            run50,
            jump,
            label
        ])

df = pd.DataFrame(data, columns=[
    "StudentID", "Date", "Height", "Weight", "BMI",
    "LungCapacity", "Run50m", "Jump", "Label"
])

csv_path = "data/students.csv"
df.to_csv(csv_path, index=False, encoding="utf-8-sig")
print(f"CSV 文件已生成：{csv_path}")
print(df.head())
