import pandas as pd
import plotly.express as px
import streamlit as st

from scripts.db_utils import get_student_info, get_student_fitness_tests
from scripts.fitness_standard import calculate_fitness_score


def generate_recommendation(row):
    """
    根据 weak_items 或各项指标生成训练建议
    """
    advice = []
    weak_items = str(row.get("weak_items", "")).strip().split(",")
    weak_items = [w.strip() for w in weak_items if w.strip()]

    if weak_items:
        if "BMI" in weak_items:
            bmi = row.get("bmi")
            if pd.notna(bmi):
                if float(bmi) < 16:
                    advice.append("注意营养摄入，增加基础力量训练")
                elif float(bmi) > 25:
                    advice.append("建议增加有氧运动，控制体重")
        if "肺活量" in weak_items:
            advice.append("建议加强慢跑和耐力训练，提高心肺功能")
        if "50米跑" in weak_items:
            advice.append("建议增加短跑和爆发力训练")
        if "立定跳远" in weak_items:
            advice.append("建议加强下肢力量和跳跃训练")
        if "耐力跑" in weak_items:
            advice.append("建议进行持续跑和间歇耐力训练")
        if "力量项目" in weak_items:
            advice.append("建议增加核心力量训练")
        if "坐位体前屈" in weak_items:
            advice.append("建议加强柔韧性和拉伸训练")
    else:
        bmi = row.get("bmi")
        lung = row.get("lung_capacity")
        sprint = row.get("sprint_50m")
        jump = row.get("standing_long_jump")
        if pd.notna(bmi):
            if float(bmi) < 16:
                advice.append("注意营养摄入，增加基础力量训练")
            elif float(bmi) > 25:
                advice.append("建议增加有氧运动，控制体重")
        if pd.notna(lung) and float(lung) < 2500:
            advice.append("建议加强慢跑和耐力训练")
        if pd.notna(sprint) and float(sprint) > 9.0:
            advice.append("建议增加短跑和爆发力训练")
        if pd.notna(jump) and float(jump) < 160:
            advice.append("建议加强下肢力量训练")

    if not advice:
        return "继续保持当前训练节奏，保持规律运动与休息。"
    return "；".join(list(dict.fromkeys(advice)))


def level_to_text(level):
    """
    体质等级映射
    """
    mapping = {"优秀": "优秀", "良好": "良好", "及格": "中等", "不及格": "差"}
    if isinstance(level, str):
        return mapping.get(level.strip(), level.strip())
    return str(level)


def run_student_fitness_dashboard(student_id):
    st.header("我的体测档案")

    student_id = str(student_id).zfill(3)
    student_info = get_student_info(student_id)
    records = get_student_fitness_tests(student_id)

    if not records:
        st.warning("未找到您的体测记录")
        return

    df = pd.DataFrame(records)
    df["test_date"] = pd.to_datetime(df["test_date"], errors="coerce")
    df = df.dropna(subset=["test_date"]).sort_values("test_date").reset_index(drop=True)

    # 最新记录
    latest = df.iloc[-1]
    latest["Recommendation"] = generate_recommendation(latest)

    # -------------------------
    # 学生基本信息
    # -------------------------
    st.subheader("基本信息")
    if student_info:
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**学号：** {student_info.get('student_id', '-')}")
        c2.markdown(f"**姓名：** {student_info.get('name', '-')}")
        c3.markdown(f"**性别：** {student_info.get('gender', '-')}")
        c4, c5, c6 = st.columns(3)
        c4.markdown(f"**年龄：** {student_info.get('age', '-')}")
        c5.markdown(f"**班级：** {student_info.get('class_name', '-')}")
        c6.markdown(f"**联系电话：** {student_info.get('phone', '-')}")
    else:
        st.info("未查询到注册信息")

    # -------------------------
    # 最新体测
    # -------------------------
    st.subheader("最新体测情况")
    c1, c2, c3 = st.columns(3)
    c1.metric("BMI", round(float(latest.get("bmi", 0)), 2))
    c1.metric("肺活量", int(float(latest.get("lung_capacity", 0))))
    c1.metric("50米跑", round(float(latest.get("sprint_50m", 0)), 2))
    c2.metric("立定跳远", int(float(latest.get("standing_long_jump", 0))))
    c2.metric("耐力跑", round(float(latest.get("endurance_run", 0)), 2))
    c2.metric("力量项目", round(float(latest.get("strength", 0)), 1))
    c3.metric("总分", round(float(latest.get("total_score", 0)), 2))
    c3.metric("等级", level_to_text(latest.get("level", "-")))
    c3.metric("体测日期", latest["test_date"].strftime("%Y-%m-%d"))

    # -------------------------
    # 短板项与训练建议
    # -------------------------
    st.subheader("短板项与训练建议")
    weak_items = str(latest.get("weak_items", "")).replace(",", "、")
    st.markdown(f"**短板项：** {weak_items if weak_items else '暂无明显短板'}")
    st.markdown(f"**训练建议：** {latest['Recommendation']}")

    # -------------------------
    # 历史记录
    # -------------------------
    st.subheader("历史体测记录")
    display_cols = [
        "test_date", "grade", "gender",
        "height_cm", "weight_kg", "bmi",
        "lung_capacity", "sprint_50m", "sit_and_reach",
        "standing_long_jump", "endurance_run", "strength",
        "total_score", "level", "weak_items"
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    df_display = df[display_cols].copy()
    df_display["test_date"] = df_display["test_date"].dt.strftime("%Y-%m-%d")
    rename_map = {
        "test_date": "体测日期",
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
    df_display = df_display.rename(columns=rename_map)
    with st.expander("展开历史体测记录"):
        st.dataframe(df_display, use_container_width=True)

    # -------------------------
    # 指标趋势图
    # -------------------------
    st.subheader("体测指标趋势")
    metrics = ["BMI", "50米跑(秒)", "立定跳远(cm)", "总分"]
    available_metrics = [m for m in metrics if m in df_display.columns]
    if not available_metrics:
        st.info("暂无可展示的趋势指标")
    else:
        metric_option = st.selectbox("选择查看指标", available_metrics)
        fig = px.line(
            df_display,
            x="体测日期",
            y=metric_option,
            markers=True,
            title=f"{metric_option} 变化趋势"
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
