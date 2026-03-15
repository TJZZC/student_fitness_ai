# scripts/plotly_interactive.py
import pandas as pd
import plotly.express as px
import os

# =========================
# 1️⃣ 获取 CSV 路径
# =========================
script_dir = os.path.dirname(__file__)
csv_path = os.path.join(script_dir, "../data/students.csv")

if not os.path.exists(csv_path):
    raise FileNotFoundError(
        f"请在 {csv_path} 创建 CSV 文件，列名: "
        "StudentID,Date,Height,Weight,BMI,LungCapacity,Run50m,Jump,Label"
    )

# =========================
# 2️⃣ 读取 CSV
# =========================
df = pd.read_csv(csv_path)
df['Date'] = pd.to_datetime(df['Date'])

# =========================
# 3️⃣ 训练建议函数
# =========================
def generate_recommendation(level):
    if level == 0:
        return "保持现有训练，多参加运动竞赛"
    elif level == 1:
        return "每周增加耐力跑或跳远训练"
    elif level == 2:
        return "重点训练心肺能力，每天适量跑步"
    else:
        return "从基础体能开始，每天轻度运动，循序渐进"

df['Recommendation'] = df['Label'].apply(generate_recommendation)
df['Pred_Label'] = df['Label']  # 演示用，直接使用 CSV Label

# =========================
# 4️⃣ 绘制交互式折线图
# =========================
fig = px.line(
    df,
    x='Date',
    y='Pred_Label',
    color='StudentID',
    markers=True,
    hover_data={
        'StudentID': True,
        'Pred_Label': True,
        'Recommendation': True,
        'Height': True,
        'Weight': True,
        'BMI': True,
        'LungCapacity': True,
        'Run50m': True,
        'Jump': True
    },
    labels={
        'Pred_Label': '体质等级 (0优秀,1良好,2中等,3差)',
        'Date': '日期',
        'StudentID': '学生编号'
    },
    title='学生体质等级动态变化（交互式，悬停查看数据与训练建议）'
)

# =========================
# 5️⃣ 更新布局
# =========================
fig.update_layout(
    yaxis=dict(tickvals=[0,1,2,3], ticktext=['优秀','良好','中等','差']),
    hovermode='closest',
    width=1200,
    height=700
)

# =========================
# 6️⃣ 显示图表
# =========================
fig.show()
