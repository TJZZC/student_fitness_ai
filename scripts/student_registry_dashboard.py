import pandas as pd
import streamlit as st
from scripts.db_utils import get_all_students


def run_student_registry_dashboard():
    st.header("学生信息管理")
    st.caption("查看学生端注册提交的信息")

    rows = get_all_students()

    if not rows:
        st.info("当前还没有学生注册信息。")
        return

    # 兼容 db_utils 返回 dict
    df = pd.DataFrame(rows).copy()

    rename_map = {
        "student_id": "学号",
        "name": "姓名",
        "gender": "性别",
        "age": "年龄",
        "class_name": "班级",
        "phone": "联系电话",
        "created_at": "注册时间"
    }

    df = df.rename(columns=rename_map)

    expected_cols = [
        "学号", "姓名", "性别", "年龄",
        "班级", "联系电话", "注册时间"
    ]

    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    # 学号统一三位
    df["学号"] = df["学号"].astype(str).str.zfill(3)

    # 时间格式优化
    if "注册时间" in df.columns:
        df["注册时间"] = pd.to_datetime(
            df["注册时间"], errors="coerce"
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

    df = df[expected_cols]

    st.subheader("已注册学生列表")
    st.dataframe(df, use_container_width=True)

    # =========================
    # 下载CSV
    # =========================
    csv_data = df.to_csv(index=False).encode("utf-8-sig")

    st.download_button(
        "下载学生信息 CSV",
        csv_data,
        "student_registry.csv",
        "text/csv"
    )
