import os
import pandas as pd
import streamlit as st
from fpdf import FPDF
import joblib


# =========================
# 报告摘要统计函数
# =========================
def build_report_summary(df):
    summary = {}

    summary["student_count"] = df["StudentID"].nunique()
    summary["avg_bmi"] = round(df["BMI"].mean(), 2)
    summary["avg_lung"] = round(df["LungCapacity"].mean(), 1)
    summary["avg_run50m"] = round(df["Run50m"].mean(), 2)
    summary["avg_jump"] = round(df["Jump"].mean(), 1)

    if "Reason" in df.columns:
        summary["risk_count"] = int((df["Reason"] != "正常").sum())
    else:
        summary["risk_count"] = 0

    if "PredLabel" in df.columns:
        summary["pred_excellent"] = int((df["PredLabel"] == "优秀").sum())
        summary["pred_good"] = int((df["PredLabel"] == "良好").sum())
        summary["pred_medium"] = int((df["PredLabel"] == "中等").sum())
        summary["pred_bad"] = int((df["PredLabel"] == "差").sum())
    else:
        summary["pred_excellent"] = 0
        summary["pred_good"] = 0
        summary["pred_medium"] = 0
        summary["pred_bad"] = 0

    return summary


# =========================
# 班级综合训练建议函数
# =========================
def generate_class_advice(df):
    advice = []

    if df["LungCapacity"].mean() < 3000:
        advice.append("班级整体心肺能力偏弱，建议每周安排2~3次耐力跑训练。")

    if df["Run50m"].mean() > 8.8:
        advice.append("班级整体速度能力有提升空间，建议增加短跑与步频训练。")

    if df["Jump"].mean() < 170:
        advice.append("班级整体下肢爆发力偏弱，建议增加跳跃和下肢力量训练。")

    if df["BMI"].mean() > 24:
        advice.append("班级平均BMI偏高，建议加强有氧运动并关注体重管理。")
    elif df["BMI"].mean() < 18.5:
        advice.append("班级平均BMI偏低，建议关注营养补充和基础力量训练。")

    if not advice:
        advice.append("班级整体体质情况较稳定，建议保持当前训练节奏。")

    return advice


# =========================
# 加载模型并生成 PredLabel
# =========================
def add_prediction_labels(df):
    script_dir = os.path.dirname(__file__)
    model_path = os.path.join(script_dir, "../models/best_next_label_model.pkl")

    if not os.path.exists(model_path):
        return df

    try:
        model = joblib.load(model_path)
    except Exception:
        return df

    feature_cols = [
        "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]

    for col in feature_cols:
        if col not in df.columns:
            return df

    label_text_map = ["优秀", "良好", "中等", "差"]

    df = df.copy()
    df["Date"] = pd.to_datetime(df["Date"])
    df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)

    pred_rows = []

    for student_id, group in df.groupby("StudentID"):
        group = group.sort_values("Date").reset_index(drop=True)

        if len(group) < 1:
            continue

        X = group[feature_cols].tail(3)

        try:
            pred_label_num = int(model.predict(X)[-1])
            pred_label_text = label_text_map[pred_label_num]
        except Exception:
            pred_label_text = "未知"

        latest_row = group.iloc[-1].copy()
        latest_row["PredLabel"] = pred_label_text
        pred_rows.append(latest_row)

    if len(pred_rows) == 0:
        return df

    latest_pred_df = pd.DataFrame(pred_rows)

    # 用最新记录生成报告摘要更合理
    return latest_pred_df


# =========================
# 普通学生明细 PDF
# =========================
def make_pdf_report(df, filename="异常学生.pdf"):
    output_dir = os.path.join(os.path.dirname(__file__), "../output")
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, filename)

    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join(os.path.dirname(__file__), "../fonts/SimSun.ttf")
    pdf.add_font("SimSun", "", font_path, uni=True)
    pdf.set_font("SimSun", "", 12)

    pdf.cell(0, 10, "学生体质异常报告：", ln=True)

    for _, row in df.iterrows():
        reason_text = row["Reason"] if "Reason" in df.columns else "无"
        line = (
            f"{row['StudentID']} | "
            f"BMI:{row['BMI']} | "
            f"肺活量:{row['LungCapacity']} | "
            f"50米跑:{row['Run50m']} | "
            f"跳远:{row['Jump']} | "
            f"原因:{reason_text}"
        )
        pdf.multi_cell(0, 8, line)

    pdf.output(pdf_path)
    return pdf_path


# =========================
# 升级版全班报告 PDF
# =========================
def make_class_report_pdf(df, filename="全班学生.pdf"):
    output_dir = os.path.join(os.path.dirname(__file__), "../output")
    os.makedirs(output_dir, exist_ok=True)

    pdf_path = os.path.join(output_dir, filename)

    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join(os.path.dirname(__file__), "../fonts/SimSun.ttf")
    pdf.add_font("SimSun", "", font_path, uni=True)
    pdf.set_font("SimSun", "", 12)

    summary = build_report_summary(df)
    class_advice = generate_class_advice(df)

    pdf.set_font("SimSun", "", 16)
    pdf.cell(0, 10, "中学生体质分析报告", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("SimSun", "", 13)
    pdf.cell(0, 10, "一、班级概况", ln=True)

    pdf.set_font("SimSun", "", 12)
    pdf.multi_cell(0, 8, f"学生总数：{summary['student_count']}人")
    pdf.multi_cell(0, 8, f"平均BMI：{summary['avg_bmi']}")
    pdf.multi_cell(0, 8, f"平均肺活量：{summary['avg_lung']}")
    pdf.multi_cell(0, 8, f"平均50米跑：{summary['avg_run50m']}秒")
    pdf.multi_cell(0, 8, f"平均跳远：{summary['avg_jump']}厘米")
    pdf.multi_cell(0, 8, f"重点关注学生人数：{summary['risk_count']}人")
    pdf.ln(2)

    pdf.set_font("SimSun", "", 13)
    pdf.cell(0, 10, "二、AI预测结果概览", ln=True)

    pdf.set_font("SimSun", "", 12)
    if "PredLabel" in df.columns:
        pdf.multi_cell(0, 8, f"预测优秀人数：{summary['pred_excellent']}人")
        pdf.multi_cell(0, 8, f"预测良好人数：{summary['pred_good']}人")
        pdf.multi_cell(0, 8, f"预测中等人数：{summary['pred_medium']}人")
        pdf.multi_cell(0, 8, f"预测较差人数：{summary['pred_bad']}人")
    else:
        pdf.multi_cell(0, 8, "当前数据中暂无 PredLabel 列，暂不显示 AI预测统计。")
    pdf.ln(2)

    pdf.set_font("SimSun", "", 13)
    pdf.cell(0, 10, "三、风险学生名单", ln=True)

    pdf.set_font("SimSun", "", 12)
    if "Reason" in df.columns:
        risk_df = df[df["Reason"] != "正常"].copy()
    else:
        risk_df = pd.DataFrame()

    if risk_df.empty:
        pdf.multi_cell(0, 8, "当前无重点风险学生。")
    else:
        show_cols = ["StudentID", "BMI", "LungCapacity", "Run50m", "Jump", "Reason"]
        for _, row in risk_df[show_cols].iterrows():
            line = (
                f"{row['StudentID']} | "
                f"BMI:{row['BMI']} | "
                f"肺活量:{row['LungCapacity']} | "
                f"50米跑:{row['Run50m']} | "
                f"跳远:{row['Jump']} | "
                f"风险:{row['Reason']}"
            )
            pdf.multi_cell(0, 8, line)
    pdf.ln(2)

    pdf.set_font("SimSun", "", 13)
    pdf.cell(0, 10, "四、综合训练建议", ln=True)

    pdf.set_font("SimSun", "", 12)
    for idx, item in enumerate(class_advice, start=1):
        pdf.multi_cell(0, 8, f"{idx}. {item}")

    pdf.output(pdf_path)
    return pdf_path


# =========================
# Excel 导出函数
# =========================
def make_excel_report(df, filename="异常学生.xlsx"):
    output_dir = os.path.join(os.path.dirname(__file__), "../output")
    os.makedirs(output_dir, exist_ok=True)

    excel_path = os.path.join(output_dir, filename)
    df.to_excel(excel_path, index=False)
    return excel_path


# =========================
# 主函数
# =========================
def run_data_dashboard():
    st.header("数据管理与报告生成")

    csv_file = st.file_uploader("上传 CSV 文件", type=["csv"])
    if csv_file is None:
        st.warning("请上传 CSV 文件")
        return

    try:
        raw_df = pd.read_csv(csv_file)
    except Exception as e:
        st.error(f"加载 CSV 文件失败: {e}")
        return

    # 原始数据用于展示
    display_df = raw_df.copy()

    # 异常值检测
    display_df["Reason"] = display_df.apply(
        lambda r: "BMI异常" if r["BMI"] < 18.5 or r["BMI"] > 24 else "正常",
        axis=1
    )
    abnormal_df = display_df[display_df["Reason"] != "正常"].copy()

    # 用“最新记录 + 预测标签”生成班级报告
    report_df = add_prediction_labels(raw_df)

    # 如果模型没跑出来 PredLabel，也补 Reason
    if "Reason" not in report_df.columns:
        report_df["Reason"] = report_df.apply(
            lambda r: "BMI异常" if r["BMI"] < 18.5 or r["BMI"] > 24 else "正常",
            axis=1
        )

    summary = build_report_summary(report_df)

    st.subheader("报告摘要预览")

    c1, c2, c3 = st.columns(3)
    c1.metric("学生总数", summary["student_count"])
    c2.metric("平均 BMI", summary["avg_bmi"])
    c3.metric("平均肺活量", summary["avg_lung"])

    c4, c5, c6 = st.columns(3)
    c4.metric("平均50米跑", summary["avg_run50m"])
    c5.metric("平均跳远", summary["avg_jump"])
    c6.metric("异常人数", summary["risk_count"])

    if "PredLabel" in report_df.columns:
        st.markdown("### AI预测结果统计")
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("预测优秀", summary["pred_excellent"])
        p2.metric("预测良好", summary["pred_good"])
        p3.metric("预测中等", summary["pred_medium"])
        p4.metric("预测差", summary["pred_bad"])

    st.subheader("原始数据")
    st.dataframe(display_df)

    st.subheader("异常学生列表")
    st.dataframe(abnormal_df)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("导出异常学生 Excel"):
            path = make_excel_report(abnormal_df, filename="异常学生.xlsx")
            st.success(f"Excel 已生成: {path}")

        if st.button("生成异常学生 PDF"):
            path = make_pdf_report(abnormal_df, filename="异常学生.pdf")
            st.success(f"PDF 已生成: {path}")

    with col2:
        if st.button("导出全班 Excel"):
            path = make_excel_report(display_df, filename="全班学生.xlsx")
            st.success(f"Excel 已生成: {path}")

        if st.button("生成全班报告 PDF"):
            path = make_class_report_pdf(report_df, filename="全班学生.pdf")
            st.success(f"PDF 已生成: {path}")
