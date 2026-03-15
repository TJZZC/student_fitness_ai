import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.db_utils import (
    get_student_info,
    add_fitness_test_record,
    get_all_fitness_tests,
    delete_fitness_test_by_id,
)
from scripts.fitness_standard import calculate_fitness_score


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def run_fitness_dashboard():
    st.subheader("体测管理模块")
    st.caption("新增、管理学生体测记录，并分析班级趋势")

    tabs = st.tabs(["体测录入", "记录管理", "班级趋势分析"])

    # =========================
    # Tab 1: 体测录入
    # =========================
    with tabs[0]:
        st.markdown("### 新增学生体测记录")

        with st.form("fitness_test_form"):
            col1, col2, col3 = st.columns(3)
            with col1:
                student_id = st.text_input("学号", placeholder="请输入已注册学号")
            with col2:
                test_date = st.date_input("测试日期")
            with col3:
                grade = st.selectbox("年级", ["七年级", "八年级", "九年级"])

            col4, col5, col6 = st.columns(3)
            with col4:
                gender = st.selectbox("性别", ["男", "女"])
            with col5:
                height_cm = st.number_input("身高(cm)", min_value=0.0, step=0.1, format="%.1f")
            with col6:
                weight_kg = st.number_input("体重(kg)", min_value=0.0, step=0.1, format="%.1f")

            col7, col8, col9 = st.columns(3)
            with col7:
                lung_capacity = st.number_input("肺活量", min_value=0.0, step=1.0)
            with col8:
                sprint_50m = st.number_input("50米跑(秒)", min_value=0.0, step=0.1)
            with col9:
                sit_and_reach = st.number_input("坐位体前屈(cm)", min_value=0.0, step=0.1)

            col10, col11, col12 = st.columns(3)
            with col10:
                standing_long_jump = st.number_input("立定跳远(cm)", min_value=0.0, step=1.0)
            with col11:
                endurance_run = st.number_input("耐力跑(秒)", min_value=0.0, step=1.0)
            with col12:
                strength = st.number_input("力量项目(次数)", min_value=0.0, step=1.0)

            submitted = st.form_submit_button("计算并保存")

        if submitted:
            student_id = student_id.strip()
            if not student_id:
                st.warning("请输入学号")
            else:
                student_info = get_student_info(student_id)
                if not student_info:
                    st.warning("该学号未注册，请先注册")
                elif height_cm <= 0 or weight_kg <= 0:
                    st.warning("身高和体重必须大于 0")
                else:
                    # 计算 BMI
                    bmi = round(weight_kg / ((height_cm / 100) ** 2), 2)
                    result = calculate_fitness_score(
                        grade=grade,
                        gender=gender,
                        bmi=bmi,
                        lung_capacity=lung_capacity,
                        sprint_50m=sprint_50m,
                        sit_and_reach=sit_and_reach,
                        standing_long_jump=standing_long_jump,
                        endurance_run=endurance_run,
                        strength=strength
                    )
                    add_fitness_test_record(
                        student_id=student_id,
                        test_date=str(test_date),
                        grade=grade,
                        gender=gender,
                        height_cm=height_cm,
                        weight_kg=weight_kg,
                        bmi=bmi,
                        lung_capacity=lung_capacity,
                        sprint_50m=sprint_50m,
                        sit_and_reach=sit_and_reach,
                        standing_long_jump=standing_long_jump,
                        endurance_run=endurance_run,
                        strength=strength,
                        score_result=result
                    )
                    st.success("体测记录已保存")

    # =========================
    # Tab 2: 体测记录管理
    # =========================
    with tabs[1]:
        st.markdown("### 体测记录管理（查看/删除）")
        all_records = get_all_fitness_tests()
        if not all_records:
            st.info("暂无体测记录")
            return

        df = pd.DataFrame(all_records)
        df["test_date"] = pd.to_datetime(df["test_date"], errors="coerce")

        # 筛选
        classes = ["全部"] + sorted(df["class_name"].dropna().astype(str).unique().tolist())
        selected_class = st.selectbox("选择班级", classes)
        filtered_df = df.copy()
        if selected_class != "全部":
            filtered_df = filtered_df[df["class_name"] == selected_class]

        student_id_kw = st.text_input("按学号筛选")
        if student_id_kw.strip():
            filtered_df = filtered_df[filtered_df["student_id"].astype(str).str.contains(student_id_kw.strip(), na=False)]

        if filtered_df.empty:
            st.info("暂无符合条件的记录")
        else:
            display_cols = ["id", "test_date", "student_id", "name", "class_name", "total_score", "level", "weak_items"]
            display_cols = [c for c in display_cols if c in filtered_df.columns]
            df_display = filtered_df[display_cols].copy()
            df_display["test_date"] = df_display["test_date"].dt.strftime("%Y-%m-%d")
            st.dataframe(df_display, use_container_width=True)

            # 删除
            st.markdown("### 删除记录")
            record_options = df_display.apply(lambda r: f"ID {r['id']} | {r['student_id']} | {r.get('name','-')} | {r.get('class_name','-')}", axis=1).tolist()
            selected_label = st.selectbox("选择要删除的记录", record_options)
            selected_id = int(selected_label.split("|")[0].split()[1])

            confirm_delete = st.checkbox("我确认要删除该记录")
            if st.button("删除选中记录"):
                if not confirm_delete:
                    st.warning("请先勾选确认删除")
                else:
                    delete_fitness_test_by_id(selected_id)
                    st.success("删除成功，请刷新页面查看最新数据")
                    st.rerun()

    # =========================
    # Tab 3: 班级趋势分析
    # =========================
    with tabs[2]:
        st.markdown("### 班级体测趋势分析")
        all_records = get_all_fitness_tests()
        if not all_records:
            st.info("暂无体测数据")
            return

        df = pd.DataFrame(all_records)
        df["test_date"] = pd.to_datetime(df["test_date"], errors="coerce")

        classes = ["全部"] + sorted(df["class_name"].dropna().astype(str).unique().tolist())
        selected_class = st.selectbox("选择班级分析", classes, key="trend_class")
        filtered_df = df.copy()
        if selected_class != "全部":
            filtered_df = filtered_df[df["class_name"] == selected_class]

        if filtered_df.empty:
            st.info("暂无数据")
            return

        # 平均值趋势
        trend_cols = ["bmi", "lung_capacity", "sprint_50m", "sit_and_reach", "standing_long_jump", "endurance_run", "strength", "total_score"]
        trend_cols = [c for c in trend_cols if c in filtered_df.columns]
        avg_df = filtered_df.groupby("test_date")[trend_cols].mean().reset_index()
        fig = px.line(avg_df, x="test_date", y=trend_cols, markers=True, title=f"{selected_class} 平均指标趋势")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        # 等级占比
        st.markdown("#### 体质等级占比")
        if "level" in filtered_df.columns:
            level_counts = filtered_df["level"].value_counts().reset_index()
            level_counts.columns = ["等级", "人数"]
            fig2 = px.pie(level_counts, names="等级", values="人数", title="等级占比")
            st.plotly_chart(fig2, use_container_width=True)

        # 短板项分布
        st.markdown("#### 短板项分布统计")
        if "weak_items" in filtered_df.columns:
            all_weak = filtered_df["weak_items"].dropna().apply(lambda x: [i.strip() for i in x.split(",")])
            flat_list = [item for sublist in all_weak for item in sublist if item]
            if flat_list:
                weak_counts = pd.Series(flat_list).value_counts().reset_index()
                weak_counts.columns = ["项目", "人数"]
                fig3 = px.bar(weak_counts, x="项目", y="人数", text="人数", title="短板项统计")
                fig3.update_traces(textposition="outside")
                st.plotly_chart(fig3, use_container_width=True)
            else:
                st.info("暂无短板项数据")
        else:
            st.info("暂无 weak_items 字段")
