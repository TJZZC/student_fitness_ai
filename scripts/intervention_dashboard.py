import os
from datetime import date, timedelta

import joblib
import pandas as pd
import streamlit as st

from scripts.db_utils import get_all_exercise_records


# =========================
# 当前风险识别
# =========================
def identify_risk(row):
    reasons = []

    bmi = row.get("BMI")
    run50m = row.get("Run50m")
    lung = row.get("LungCapacity")
    jump = row.get("Jump")
    label = row.get("Label")

    if pd.notna(bmi):
        if bmi >= 28:
            reasons.append("BMI偏高")
        elif bmi <= 16:
            reasons.append("BMI偏低")

    if pd.notna(run50m) and run50m >= 9.0:
        reasons.append("50米跑偏慢")

    if pd.notna(lung) and lung <= 2600:
        reasons.append("肺活量偏低")

    if pd.notna(jump) and jump <= 160:
        reasons.append("跳远偏弱")

    if pd.notna(label) and label >= 2:
        reasons.append("体质等级需关注")

    return "、".join(reasons) if reasons else "正常"


# =========================
# 读取体测数据
# =========================
def load_students_data():
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

    numeric_cols = [
        "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# =========================
# 获取最近一次体测记录
# =========================
def get_latest_students(df):
    if df.empty:
        return df

    latest_df = (
        df.sort_values("Date")
        .groupby("StudentID", as_index=False)
        .tail(1)
        .copy()
    )
    return latest_df


# =========================
# 运动记录标准化
# =========================
def normalize_exercise_df(rows):
    """
    兼容 db_utils.get_all_exercise_records() 返回的字典列表
    """
    if not rows:
        return pd.DataFrame()

    exercise_df = pd.DataFrame(rows).copy()

    rename_map = {
        "student_id": "StudentID",
        "name": "姓名",
        "class_name": "班级",
        "exercise_date": "运动日期",
        "exercise_type": "运动类型",
        "duration_minutes": "运动时长(分钟)",
        "intensity": "运动强度",
        "remark": "备注",
        "created_at": "提交时间"
    }
    exercise_df = exercise_df.rename(columns=rename_map)

    expected_cols = [
        "StudentID", "姓名", "班级", "运动日期", "运动类型",
        "运动时长(分钟)", "运动强度", "备注", "提交时间"
    ]
    for col in expected_cols:
        if col not in exercise_df.columns:
            exercise_df[col] = None

    exercise_df["StudentID"] = exercise_df["StudentID"].astype(str).str.zfill(3)

    # 关键修复：统一转成 Python date，避免 datetime64 和 date 比较报错
    exercise_df["运动日期"] = pd.to_datetime(exercise_df["运动日期"], errors="coerce")
    exercise_df = exercise_df.dropna(subset=["运动日期"]).copy()
    exercise_df["运动日期"] = exercise_df["运动日期"].dt.date

    exercise_df["运动时长(分钟)"] = pd.to_numeric(
        exercise_df["运动时长(分钟)"], errors="coerce"
    ).fillna(0)

    return exercise_df


# =========================
# 低活跃学生识别
# =========================
def get_low_activity_students():
    rows = get_all_exercise_records()

    if not rows:
        return pd.DataFrame(columns=["StudentID", "近7天打卡次数", "活跃度状态"])

    exercise_df = normalize_exercise_df(rows)

    if exercise_df.empty:
        return pd.DataFrame(columns=["StudentID", "近7天打卡次数", "活跃度状态"])

    today = date.today()
    last_7_days = today - timedelta(days=6)

    recent_df = exercise_df[exercise_df["运动日期"] >= last_7_days].copy()

    if recent_df.empty:
        return pd.DataFrame(columns=["StudentID", "近7天打卡次数", "活跃度状态"])

    stat_df = (
        recent_df.groupby("StudentID")
        .size()
        .reset_index(name="近7天打卡次数")
    )

    stat_df["活跃度状态"] = stat_df["近7天打卡次数"].apply(
        lambda x: "低活跃" if x < 2 else "正常"
    )

    return stat_df


# =========================
# AI 风险预测
# =========================
def get_ai_risk_students(latest_df):
    script_dir = os.path.dirname(__file__)
    model_path = os.path.join(script_dir, "../models/risk_predict_model.pkl")

    if latest_df.empty or not os.path.exists(model_path):
        return pd.DataFrame(columns=["StudentID", "风险概率", "AI风险状态"])

    feature_cols = [
        "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]

    missing_cols = [c for c in feature_cols if c not in latest_df.columns]
    if missing_cols:
        return pd.DataFrame(columns=["StudentID", "风险概率", "AI风险状态"])

    try:
        input_df = latest_df[feature_cols].copy()
        input_df = input_df.fillna(input_df.median(numeric_only=True))
        input_df = input_df.fillna(0)

        model = joblib.load(model_path)
        pred = model.predict(input_df)
        prob = model.predict_proba(input_df)[:, 1]
    except Exception:
        return pd.DataFrame(columns=["StudentID", "风险概率", "AI风险状态"])

    result_df = latest_df[["StudentID"]].copy()
    result_df["风险概率"] = prob
    result_df["AI风险状态"] = ["预测高风险" if p == 1 else "正常" for p in pred]

    return result_df


# =========================
# 页面主函数
# =========================
def run_intervention_dashboard():
    st.header("重点干预名单")
    st.caption("综合当前体质风险、家庭运动活跃度与AI预测结果，识别需要重点关注的学生")

    df = load_students_data()
    if df.empty:
        st.warning("未找到有效的 students.csv 数据，无法生成重点干预名单。")
        return

    latest_df = get_latest_students(df)
    latest_df["当前风险"] = latest_df.apply(identify_risk, axis=1)

    # 当前风险学生
    current_risk_df = latest_df[latest_df["当前风险"] != "正常"][["StudentID", "当前风险"]].copy()

    # 低活跃学生
    low_activity_df = get_low_activity_students()

    # 为了让没打卡的学生也能识别成低活跃
    all_students = latest_df[["StudentID"]].copy()
    low_activity_df = all_students.merge(low_activity_df, on="StudentID", how="left")
    low_activity_df["近7天打卡次数"] = low_activity_df["近7天打卡次数"].fillna(0).astype(int)
    low_activity_df["活跃度状态"] = low_activity_df["活跃度状态"].fillna("低活跃")

    # AI 风险学生
    ai_risk_df = get_ai_risk_students(latest_df)

    # 合并
    merged_df = latest_df[["StudentID"]].copy()
    merged_df = merged_df.merge(current_risk_df, on="StudentID", how="left")
    merged_df = merged_df.merge(low_activity_df, on="StudentID", how="left")
    merged_df = merged_df.merge(ai_risk_df, on="StudentID", how="left")

    merged_df["当前风险"] = merged_df["当前风险"].fillna("正常")
    merged_df["活跃度状态"] = merged_df["活跃度状态"].fillna("正常")
    merged_df["风险概率"] = merged_df["风险概率"].fillna(0)
    merged_df["AI风险状态"] = merged_df["AI风险状态"].fillna("正常")

    merged_df["是否重点干预"] = merged_df.apply(
        lambda row: "是" if (
            row["当前风险"] != "正常" or
            row["活跃度状态"] == "低活跃" or
            row["AI风险状态"] == "预测高风险"
        ) else "否",
        axis=1
    )

    focus_df = merged_df[merged_df["是否重点干预"] == "是"].copy()

    # =========================
    # 概览
    # =========================
    c1, c2, c3 = st.columns(3)
    c1.metric("当前高风险学生", int((merged_df["当前风险"] != "正常").sum()))
    c2.metric("低活跃学生", int((merged_df["活跃度状态"] == "低活跃").sum()))
    c3.metric("AI预测高风险学生", int((merged_df["AI风险状态"] == "预测高风险").sum()))

    # =========================
    # 重点干预名单
    # =========================
    st.markdown("### 综合重点干预名单")

    if focus_df.empty:
        st.success("当前暂无需要重点干预的学生。")
    else:
        show_df = focus_df[[
            "StudentID", "当前风险", "近7天打卡次数",
            "活跃度状态", "风险概率", "AI风险状态"
        ]].copy()

        show_df = show_df.rename(columns={
            "StudentID": "学号"
        })

        st.dataframe(
            show_df.style.background_gradient(
                subset=["风险概率"],
                cmap="Reds"
            ),
            use_container_width=True
        )

    # =========================
    # 可下载 CSV
    # =========================
    csv_df = focus_df[[
        "StudentID", "当前风险", "近7天打卡次数",
        "活跃度状态", "风险概率", "AI风险状态"
    ]].copy()

    csv_data = csv_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下载重点干预名单 CSV",
        csv_data,
        "重点干预名单.csv",
        "text/csv"
    )
