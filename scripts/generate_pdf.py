from fpdf import FPDF
import os

# 创建 PDF 对象
pdf = FPDF()
pdf.add_page()

# 添加中文字体
font_path = os.path.join("fonts", "SimSun.ttf")  # 确保路径正确
pdf.add_font("SimSun", "", font_path, uni=True)  # uni=True 支持中文
pdf.set_font("SimSun", "", 12)

# 添加标题
pdf.cell(0, 10, "学生体质异常报告：", ln=True)

# 添加内容
pdf.multi_cell(0, 8, "001 | BMI:21.5 | 肺活量:3200 | 50米跑:8.5 | 跳远:185 | 原因:BMI异常")

# 输出 PDF
pdf.output("异常学生.pdf")

print("PDF 已生成：异常学生.pdf")
