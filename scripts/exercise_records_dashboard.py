import pandas as pd
import streamlit as st
from scripts.db_utils import get_all_exercise_records


def run_exercise_records_dashboard():
    st.header("家庭运动记录管理")
    st.caption("查看学生在家运动打卡情况，支持筛选与导出")

    rows = get_all_exercise_records()

    if not rows:
        st.info("当前还没有家庭运动打卡记录。")
        return

    df = pd.DataFrame(
        rows,
        columns=[
            "学号", "姓名", "班级", "运动日期", "运动类型",
            "运动时长(分钟)", "运动强度", "备注", "提交时间"
        ]
    )

    # =========================
    # 筛选区
    # =========================
    st.subheader("筛选条件")

    col1, col2, col3 = st.columns(3)

    with col1:
        class_options = ["全部"] + sorted([x for x in df["班级"].dropna().unique().tolist() if x != ""])
        selected_class = st.selectbox("选择班级", class_options)

    with col2:
        type_options = ["全部"] + sorted(df["运动类型"].dropna().unique().tolist())
        selected_type = st.selectbox("选择运动类型", type_options)

    with col3:
        intensity_options = ["全部"] + sorted(df["运动强度"].dropna().unique().tolist())
        selected_intensity = st.selectbox("选择运动强度", intensity_options)

    filtered_df = df.copy()

    if selected_class != "全部":
        filtered_df = filtered_df[filtered_df["班级"] == selected_class]

    if selected_type != "全部":
        filtered_df = filtered_df[filtered_df["运动类型"] == selected_type]

    if selected_intensity != "全部":
        filtered_df = filtered_df[filtered_df["运动强度"] == selected_intensity]

    # =========================
    # 统计概览
    # =========================
    st.subheader("运动打卡概览")

    total_records = len(filtered_df)
    total_students = filtered_df["学号"].nunique()
    avg_duration = round(filtered_df["运动时长(分钟)"].mean(), 1) if total_records > 0 else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("打卡总次数", total_records)
    c2.metric("参与学生数", total_students)
    c3.metric("平均运动时长", avg_duration)

    # =========================
    # 数据表
    # =========================
    st.subheader("家庭运动记录列表")
    st.dataframe(filtered_df, use_container_width=True)

    # =========================
    # 导出 CSV
    # =========================
    csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下载家庭运动记录 CSV",
        csv_data,
        "exercise_records.csv",
        "text/csv"
    )
