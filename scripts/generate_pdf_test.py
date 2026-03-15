from fpdf import FPDF
import os

# =========================
# 1. 创建输出目录
# =========================
output_dir = os.path.join(os.path.dirname(__file__), "../output")
os.makedirs(output_dir, exist_ok=True)

# =========================
# 2. 初始化 PDF
# =========================
pdf = FPDF()
pdf.add_page()

# =========================
# 3. 添加中文字体
# =========================
font_path = os.path.join(os.path.dirname(__file__), "../fonts/SimSun.ttf")
pdf.add_font("SimSun", "", font_path, uni=True)
pdf.set_font("SimSun", "", 12)

# =========================
# 4. 写入内容
# =========================
pdf.cell(0, 10, "学生体质异常报告：", ln=True)
pdf.multi_cell(0, 8, "001 | BMI:21.5 | 肺活量:3200 | 50米跑:8.5 | 跳远:185 | 原因:BMI异常")

# =========================
# 5. 输出 PDF
# =========================
output_file = os.path.join(output_dir, "异常学生.pdf")
pdf.output(output_file)

print(f"PDF 已生成: {output_file}")
