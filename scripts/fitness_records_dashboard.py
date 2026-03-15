import pandas as pd
import streamlit as st

from scripts.db_utils import (
    get_all_fitness_tests,
    delete_fitness_test_by_id,
)


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def run_fitness_records_dashboard():
    st.subheader("体测记录管理")
    st.caption("支持查看、筛选和删除学生体测记录")

    all_records = get_all_fitness_tests()

    if not all_records:
        st.info("当前暂无体测记录。")
        return

    df = pd.DataFrame(all_records)

    # 日期和数值字段处理
    if "test_date" in df.columns:
        df["test_date"] = pd.to_datetime(df["test_date"], errors="coerce")

    numeric_cols = [
        "height_cm", "weight_kg", "bmi",
        "lung_capacity", "sprint_50m", "sit_and_reach",
        "standing_long_jump", "endurance_run", "strength",
        "total_score"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # =========================
    # 筛选区
    # =========================
    st.markdown("### 查询筛选")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        student_id_kw = st.text_input("按学号筛选")

    with col2:
        name_kw = st.text_input("按姓名筛选")

    with col3:
        class_options = ["全部"] + sorted(
            [c for c in df["class_name"].dropna().astype(str).unique().tolist() if c.strip()]
        ) if "class_name" in df.columns else ["全部"]
        selected_class = st.selectbox("按班级筛选", class_options)

    with col4:
        level_options = ["全部"] + sorted(
            [c for c in df["level"].dropna().astype(str).unique().tolist() if c.strip()]
        ) if "level" in df.columns else ["全部"]
        selected_level = st.selectbox("按等级筛选", level_options)

    filtered_df = df.copy()

    if student_id_kw.strip():
        filtered_df = filtered_df[
            filtered_df["student_id"].astype(str).str.contains(student_id_kw.strip(), na=False)
        ]

    if name_kw.strip() and "name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["name"].astype(str).str.contains(name_kw.strip(), na=False)
        ]

    if selected_class != "全部" and "class_name" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["class_name"].astype(str) == selected_class
        ]

    if selected_level != "全部" and "level" in filtered_df.columns:
        filtered_df = filtered_df[
            filtered_df["level"].astype(str) == selected_level
        ]

    if filtered_df.empty:
        st.warning("没有符合条件的体测记录。")
        return

    # =========================
    # 统计概览
    # =========================
    st.markdown("### 数据概览")

    a, b, c, d = st.columns(4)
    a.metric("记录总数", len(filtered_df))
    b.metric("学生人数", filtered_df["student_id"].nunique() if "student_id" in filtered_df.columns else 0)
    c.metric("平均总分", round(filtered_df["total_score"].mean(), 2) if "total_score" in filtered_df.columns else 0)
    d.metric("最高总分", round(filtered_df["total_score"].max(), 2) if "total_score" in filtered_df.columns else 0)

    # =========================
    # 明细列表
    # =========================
    st.markdown("### 体测记录明细")

    display_cols = [
        "id", "test_date", "student_id", "name", "class_name",
        "grade", "gender", "height_cm", "weight_kg", "bmi",
        "lung_capacity", "sprint_50m", "sit_and_reach",
        "standing_long_jump", "endurance_run", "strength",
        "total_score", "level", "weak_items"
    ]
    display_cols = [c for c in display_cols if c in filtered_df.columns]

    display_df = filtered_df[display_cols].copy()

    if "test_date" in display_df.columns:
        display_df["test_date"] = display_df["test_date"].dt.strftime("%Y-%m-%d")

    rename_map = {
        "id": "记录ID",
        "test_date": "体测日期",
        "student_id": "学号",
        "name": "姓名",
        "class_name": "班级",
        "grade": "年级",
        "gender": "性别",
        "height_cm": "身高(cm)",
        "weight_kg": "体重(kg)",
        "bmi": "BMI",
        "lung_capacity": "肺活量",
        "sprint_50m": "50米跑(秒)",
        "sit_and_reach": "坐位体前屈(cm)",
        "standing_long_jump": "立定跳远(cm)",
        "endurance_run": "耐力跑(秒)",
        "strength": "力量项目(次数)",
        "total_score": "总分",
        "level": "等级",
        "weak_items": "短板项"
    }
    display_df = display_df.rename(columns=rename_map)

    st.dataframe(display_df, use_container_width=True)

    # =========================
    # 单条记录详情
    # =========================
    st.markdown("### 单条记录详情")

    record_options = []
    option_to_id = {}

    for _, row in filtered_df.iterrows():
        record_id = row.get("id")
        test_date = row.get("test_date")
        test_date_str = test_date.strftime("%Y-%m-%d") if pd.notna(test_date) else "-"
        label = (
            f"ID {record_id} | "
            f"{safe_text(row.get('student_id'))} | "
            f"{safe_text(row.get('name'))} | "
            f"{safe_text(row.get('class_name'))} | "
            f"{test_date_str}"
        )
        record_options.append(label)
        option_to_id[label] = record_id

    selected_label = st.selectbox("选择一条记录查看详情", record_options)
    selected_id = option_to_id[selected_label]

    selected_row = filtered_df[filtered_df["id"] == selected_id].iloc[0]

    c1, c2, c3 = st.columns(3)
    c1.metric("学号", safe_text(selected_row.get("student_id")))
    c2.metric("姓名", safe_text(selected_row.get("name")))
    c3.metric("班级", safe_text(selected_row.get("class_name")))

    d1, d2, d3 = st.columns(3)
    d1.metric("总分", "-" if pd.isna(selected_row.get("total_score")) else round(float(selected_row["total_score"]), 2))
    d2.metric("等级", safe_text(selected_row.get("level")))
    d3.metric(
        "体测日期",
        selected_row["test_date"].strftime("%Y-%m-%d") if pd.notna(selected_row.get("test_date")) else "-"
    )

    st.markdown("#### 项目明细")
    e1, e2 = st.columns(2)

    with e1:
        st.write(f"**身高(cm)：** {selected_row.get('height_cm', '-')}")
        st.write(f"**体重(kg)：** {selected_row.get('weight_kg', '-')}")
        st.write(f"**BMI：** {selected_row.get('bmi', '-')}")
        st.write(f"**肺活量：** {selected_row.get('lung_capacity', '-')}")
        st.write(f"**50米跑(秒)：** {selected_row.get('sprint_50m', '-')}")

    with e2:
        st.write(f"**坐位体前屈(cm)：** {selected_row.get('sit_and_reach', '-')}")
        st.write(f"**立定跳远(cm)：** {selected_row.get('standing_long_jump', '-')}")
        st.write(f"**耐力跑(秒)：** {selected_row.get('endurance_run', '-')}")
        st.write(f"**力量项目(次数)：** {selected_row.get('strength', '-')}")
        st.write(f"**短板项：** {safe_text(selected_row.get('weak_items')).replace(',', '、')}")

    # =========================
    # 删除操作
    # =========================
    st.markdown("### 删除体测记录")
    st.warning("删除后不可恢复，请谨慎操作。")

    confirm_delete = st.checkbox("我确认要删除当前选中的体测记录")

    if st.button("删除当前记录", type="primary"):
        if not confirm_delete:
            st.warning("请先勾选确认删除。")
        else:
            try:
                delete_fitness_test_by_id(selected_id)
                st.success("体测记录删除成功，请刷新页面查看最新结果。")
                st.rerun()
            except Exception as e:
                st.error(f"删除失败：{e}")
