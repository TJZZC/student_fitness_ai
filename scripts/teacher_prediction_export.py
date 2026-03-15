import os
import pandas as pd
import streamlit as st
from fpdf import FPDF

from scripts.visual_dashboard import (
    train_multi_models,
    predict_and_advise,
    label_text_map
)


# =========================
# 读取班级体测数据
# =========================
def get_class_records():
    script_dir = os.path.dirname(__file__)
    csv_path = os.path.join(script_dir, "../data/students.csv")

    if not os.path.exists(csv_path):
        return pd.DataFrame()

    try:
        df = pd.read_csv(csv_path)
    except Exception:
        return pd.DataFrame()

    required_cols = [
        "StudentID", "Date", "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        return pd.DataFrame()

    df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"]).copy()

    return df


# =========================
# 导出 PDF
# =========================
def make_pdf_report(df, filename="班级预测.pdf"):
    output_dir = os.path.join(os.path.dirname(__file__), "../output")
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, filename)

    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join(os.path.dirname(__file__), "../fonts/SimSun.ttf")
    pdf.add_font("SimSun", "", font_path, uni=True)
    pdf.set_font("SimSun", "", 12)

    pdf.cell(0, 10, "班级学生下一次体质等级预测报告", ln=True)
    pdf.ln(4)

    for _, row in df.iterrows():
        line = (
            f"{row['StudentID']} | "
            f"综合预测:{row['综合预测']} | "
            f"心肺:{row['心肺预测']} | "
            f"速度:{row['速度预测']} | "
            f"力量:{row['力量预测']}"
        )
        pdf.multi_cell(0, 8, line)

    pdf.output(pdf_path)
    return pdf_path


# =========================
# 导出 Excel
# =========================
def make_excel_report(df, filename="班级预测.xlsx"):
    output_dir = os.path.join(os.path.dirname(__file__), "../output")
    os.makedirs(output_dir, exist_ok=True)
    excel_path = os.path.join(output_dir, filename)
    df.to_excel(excel_path, index=False)
    return excel_path


# =========================
# 页面主函数
# =========================
def run_teacher_prediction_export():
    st.subheader("班级 AI 预测汇总导出")

    df_class = get_class_records()
    if df_class.empty:
        st.warning("未找到可用于预测的班级体测数据，请检查 data/students.csv 是否存在且字段完整。")
        return

    models, model_status = train_multi_models(df_class)
    st.caption(f"模型状态：{model_status}")

    if models is None:
        st.warning("当前样本不足，无法完成班级预测。")
        return

    student_list = sorted(df_class["StudentID"].unique().tolist())
    records = []

    for student_id in student_list:
        ai_result, msg = predict_and_advise(student_id, df_class, models)
        if ai_result is not None:
            row = {
                "StudentID": student_id,
                "综合预测": label_text_map[ai_result["pred_result"]["Label"]],
                "心肺预测": label_text_map[ai_result["pred_result"]["CardioLabel"]],
                "速度预测": label_text_map[ai_result["pred_result"]["SpeedLabel"]],
                "力量预测": label_text_map[ai_result["pred_result"]["StrengthLabel"]],
                "综合趋势": ai_result["trend_result"]["OverallTrend"],
                "心肺趋势": ai_result["trend_result"]["CardioTrend"],
                "速度趋势": ai_result["trend_result"]["SpeedTrend"],
                "力量趋势": ai_result["trend_result"]["StrengthTrend"],
                "训练建议": "；".join(ai_result["advice_lines"]),
                "每周训练计划": "；".join(ai_result["weekly_plan"])
            }
            records.append(row)

    if not records:
        st.warning("当前学生历史记录不足，无法生成预测结果。")
        return

    df_export = pd.DataFrame(records)
    st.dataframe(df_export, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("导出 Excel"):
            excel_path = make_excel_report(df_export)
            st.success(f"Excel 已生成: {excel_path}")

    with col2:
        if st.button("导出 PDF"):
            pdf_path = make_pdf_report(df_export)
            st.success(f"PDF 已生成: {pdf_path}")
