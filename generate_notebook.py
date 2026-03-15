import json
import os

# 确保 notebooks 文件夹存在
os.makedirs("notebooks", exist_ok=True)

# Notebook 内容
notebook_content = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# 学生体质数据探索与折线可视化\n",
    "这个 Notebook 用于探索学生体测数据、绘制每个学生的折线趋势，并显示训练建议。"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import plotly.express as px\n",
    "import os\n",
    "\n",
    "# CSV 文件路径\n",
    "csv_path = os.path.join('..', 'data', 'students.csv')\n",
    "df = pd.read_csv(csv_path)\n",
    "df['Date'] = pd.to_datetime(df['Date'])\n",
    "\n",
    "# 训练建议函数\n",
    "def generate_recommendation(level):\n",
    "    if level == 0:\n",
    "        return \"保持现有训练，多参加运动竞赛\"\n",
    "    elif level == 1:\n",
    "        return \"每周增加耐力跑或跳远训练\"\n",
    "    elif level == 2:\n",
    "        return \"重点训练心肺能力，每天适量跑步\"\n",
    "    else:\n",
    "        return \"从基础体能开始，每天轻度运动，循序渐进\"\n",
    "\n",
    "df['Recommendation'] = df['Label'].apply(generate_recommendation)\n",
    "df['Pred_Label'] = df['Label']\n",
    "\n",
    "# 绘制交互式折线图\n",
    "fig = px.line(\n",
    "    df,\n",
    "    x='Date',\n",
    "    y='Pred_Label',\n",
    "    color='StudentID',\n",
    "    markers=True,\n",
    "    hover_data={\n",
    "        'StudentID': True,\n",
    "        'Pred_Label': True,\n",
    "        'Recommendation': True,\n",
    "        'Height': True,\n",
    "        'Weight': True,\n",
    "        'BMI': True,\n",
    "        'LungCapacity': True,\n",
    "        'Run50m': True,\n",
    "        'Jump': True\n",
    "    },\n",
    "    labels={'Pred_Label': '体质等级 (0优秀,1良好,2中等,3差)', 'Date': '日期', 'StudentID': '学生编号'},\n",
    "    title='学生体质等级动态变化（交互式，悬停查看数据与训练建议）'\n",
    ")\n",
    "\n",
    "fig.update_layout(\n",
    "    yaxis=dict(tickvals=[0,1,2,3], ticktext=['优秀','良好','中等','差']),\n",
    "    hovermode='closest',\n",
    "    width=1200,\n",
    "    height=700\n",
    ")\n",
    "\n",
    "fig.show()"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "name": "python",
   "version": "3.10"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}

# 保存 Notebook 文件
notebook_path = "notebooks/explore_student_fitness.ipynb"
with open(notebook_path, "w", encoding="utf-8") as f:
    json.dump(notebook_content, f, ensure_ascii=False, indent=2)

print(f"Notebook 文件已生成：{notebook_path}")
