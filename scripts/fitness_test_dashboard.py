import streamlit as st
from scripts.fitness_standard import calculate_fitness_score
from scripts.db_utils import add_fitness_test_record, get_student_info


def calculate_bmi(height_cm, weight_kg):
    """计算 BMI"""
    if height_cm is None or weight_kg is None:
        return 0.0

    if height_cm <= 0 or weight_kg <= 0:
        return 0.0

    height_m = float(height_cm) / 100
    return round(float(weight_kg) / (height_m ** 2), 2)


def run_fitness_test_dashboard():
    st.subheader("体测成绩录入与标准评分")
    st.caption("录入学生体测原始数据，自动计算 BMI、总分、等级和短板项")

    with st.form("fitness_test_form"):
        st.markdown("### 基本信息")
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

        st.markdown("### 体测项目")
        col7, col8, col9 = st.columns(3)

        with col7:
            lung_capacity = st.number_input("肺活量", min_value=0.0, step=1.0, format="%.1f")

        with col8:
            sprint_50m = st.number_input("50米跑(秒)", min_value=0.0, step=0.1, format="%.1f")

        with col9:
            sit_and_reach = st.number_input("坐位体前屈(cm)", step=0.1, format="%.1f")

        col10, col11, col12 = st.columns(3)

        with col10:
            standing_long_jump = st.number_input("立定跳远(cm)", min_value=0.0, step=1.0, format="%.1f")

        with col11:
            endurance_run = st.number_input("耐力跑(秒)", min_value=0.0, step=1.0, format="%.1f")

        with col12:
            strength = st.number_input("力量项目(次数)", min_value=0.0, step=1.0, format="%.1f")

        submitted = st.form_submit_button("计算并保存")

    if submitted:
        student_id = student_id.strip()

        if not student_id:
            st.warning("请输入学号")
            return

        student_info = get_student_info(student_id)
        if not student_info:
            st.warning("该学号未注册，请先到“学生信息管理”中完成注册")
            return

        if height_cm <= 0 or weight_kg <= 0:
            st.warning("身高和体重必须大于 0")
            return

        bmi = calculate_bmi(height_cm, weight_kg)

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

        st.markdown("### 学生信息")
        info_col1, info_col2, info_col3, info_col4 = st.columns(4)
        info_col1.metric("学号", student_id)
        info_col2.metric("姓名", student_info.get("name", ""))
        info_col3.metric("班级", student_info.get("class_name", ""))
        info_col4.metric("性别", gender)

        st.markdown("### 综合结果")
        a, b, c = st.columns(3)
        a.metric("BMI", bmi)
        b.metric("总分", result.total_score)
        c.metric("等级", result.level)

        st.markdown("### 单项评分")
        col_a, col_b = st.columns(2)

        with col_a:
            st.write(f"**BMI：** {result.bmi_score}")
            st.write(f"**肺活量：** {result.lung_capacity_score}")
            st.write(f"**50米跑：** {result.sprint_50m_score}")
            st.write(f"**坐位体前屈：** {result.sit_and_reach_score}")

        with col_b:
            st.write(f"**立定跳远：** {result.standing_long_jump_score}")
            st.write(f"**耐力跑：** {result.endurance_score}")
            st.write(f"**力量项目：** {result.strength_score}")
            st.write(f"**短板项：** {'、'.join(result.weak_items)}")

        st.info("当前评分规则为项目演示版，后续可替换为正式国家学生体质健康标准映射表。")
