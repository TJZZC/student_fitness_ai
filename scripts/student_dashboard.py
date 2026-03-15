import pandas as pd
import plotly.express as px
import streamlit as st

from scripts.db_utils import get_student_info, get_student_fitness_tests


def generate_recommendation(row):
    """
    根据最新体测结果生成简单训练建议
    优先使用 weak_items；如果没有，则回退到具体指标判断
    """
    advice = []

    weak_items = str(row.get("weak_items", "")).strip()
    weak_list = [item.strip() for item in weak_items.split(",") if item.strip()]

    if weak_list:
        if "BMI" in weak_list:
            bmi = row.get("bmi")
            if pd.notna(bmi):
                if float(bmi) < 16:
                    advice.append("注意营养摄入，适当增加优质蛋白和基础力量训练")
                elif float(bmi) > 25:
                    advice.append("建议增加有氧运动频率，配合饮食管理控制体重")
                else:
                    advice.append("建议保持规律作息和适量运动，持续维持良好体成分")

        if "肺活量" in weak_list:
            advice.append("建议加强慢跑、间歇跑和呼吸训练，提高心肺功能")

        if "50米跑" in weak_list:
            advice.append("建议增加短跑、加速跑和下肢爆发力训练")

        if "坐位体前屈" in weak_list:
            advice.append("建议加强拉伸训练，提升柔韧性和关节活动度")

        if "立定跳远" in weak_list:
            advice.append("建议加强下肢力量、跳跃和核心稳定训练")

        if "耐力跑" in weak_list:
            advice.append("建议进行持续跑和间歇耐力训练，提高有氧耐力")

        if "力量项目" in weak_list:
            advice.append("建议增加核心力量与专项力量训练，提高基础力量水平")

    else:
        bmi = row.get("bmi")
        lung = row.get("lung_capacity")
        run50m = row.get("sprint_50m")
        jump = row.get("standing_long_jump")

        if pd.notna(bmi):
            if float(bmi) < 16:
                advice.append("注意营养摄入，增加基础力量训练")
            elif float(bmi) > 25:
                advice.append("建议增加有氧运动，控制体重")

        if pd.notna(lung) and float(lung) < 2500:
            advice.append("建议加强慢跑和耐力训练，提高心肺功能")

        if pd.notna(run50m) and float(run50m) > 9.0:
            advice.append("建议增加短跑和爆发力训练")

        if pd.notna(jump) and float(jump) < 160:
            advice.append("建议加强下肢力量和跳跃训练")

    if not advice:
        return "继续保持当前训练节奏，坚持规律运动与充足休息。"

    # 去重
    advice = list(dict.fromkeys(advice))
    return "；".join(advice)


def level_to_text(level):
    """
    兼容旧逻辑与新逻辑
    新表里通常直接存：优秀 / 良好 / 及格 / 不及格
    """
    mapping = {
        0: "优秀",
        1: "良好",
        2: "中等",
        3: "差"
    }

    try:
        if isinstance(level, str):
            level = level.strip()
            if level in ["优秀", "良好", "及格", "不及格", "中等", "差"]:
                return level
        return mapping.get(int(level), str(level))
    except Exception:
        return str(level)


def run_student_dashboard(student_id):
    st.header("学生个人体测档案")

    student_id = str(student_id).zfill(3)

    # =========================
    # 读取数据库体测记录
    # =========================
    records = get_student_fitness_tests(student_id)

    if not records:
        st.warning("未找到该学生体测数据。")
        return

    student_df = pd.DataFrame(records)

    # 日期处理
    if "test_date" in student_df.columns:
        student_df["test_date"] = pd.to_datetime(student_df["test_date"], errors="coerce")

    student_df = student_df.dropna(subset=["test_date"]).copy()
    student_df = student_df.sort_values("test_date").reset_index(drop=True)

    if student_df.empty:
        st.warning("该学生暂无有效体测日期数据。")
        return

    # 数值字段转数值
    numeric_cols = [
        "height_cm", "weight_kg", "bmi",
        "lung_capacity", "sprint_50m", "sit_and_reach",
        "standing_long_jump", "endurance_run", "strength",
        "bmi_score", "lung_capacity_score", "sprint_50m_score",
        "sit_and_reach_score", "standing_long_jump_score",
        "endurance_score", "strength_score", "total_score"
    ]
    for col in numeric_cols:
        if col in student_df.columns:
            student_df[col] = pd.to_numeric(student_df[col], errors="coerce")

    student_df["Recommendation"] = student_df.apply(generate_recommendation, axis=1)
    latest = student_df.iloc[-1]

    # =========================
    # 注册信息展示
    # =========================
    st.subheader("学生基本信息")

    student_info = get_student_info(student_id)

    if student_info:
        a1, a2, a3 = st.columns(3)
        a1.markdown(f"**学号：** {student_info.get('student_id', '-')}")
        a2.markdown(f"**姓名：** {student_info.get('name', '-')}")
        a3.markdown(f"**性别：** {student_info.get('gender', '-')}")

        a4, a5, a6 = st.columns(3)
        a4.markdown(f"**年龄：** {student_info.get('age', '-')}")
        a5.markdown(f"**班级：** {student_info.get('class_name', '-')}")
        a6.markdown(f"**联系电话：** {student_info.get('phone', '-')}")
    else:
        st.info("暂未查询到该学生注册档案信息。")

    # =========================
    # 最新体测情况
    # =========================
    st.subheader("我的最新体测情况")

    c1, c2, c3 = st.columns(3)

    with c1:
        st.metric("BMI", "-" if pd.isna(latest.get("bmi")) else round(float(latest["bmi"]), 2))
        st.metric("肺活量", "-" if pd.isna(latest.get("lung_capacity")) else int(float(latest["lung_capacity"])))
        st.metric("50米跑", "-" if pd.isna(latest.get("sprint_50m")) else round(float(latest["sprint_50m"]), 2))

    with c2:
        st.metric("立定跳远", "-" if pd.isna(latest.get("standing_long_jump")) else int(float(latest["standing_long_jump"])))
        st.metric("耐力跑", "-" if pd.isna(latest.get("endurance_run")) else round(float(latest["endurance_run"]), 1))
        st.metric("力量项目", "-" if pd.isna(latest.get("strength")) else round(float(latest["strength"]), 1))

    with c3:
        st.metric("总分", "-" if pd.isna(latest.get("total_score")) else round(float(latest["total_score"]), 2))
        st.metric("体质等级", level_to_text(latest.get("level", "-")))
        st.metric("体测日期", latest["test_date"].strftime("%Y-%m-%d"))

    # =========================
    # 短板项
    # =========================
    st.subheader("我的短板项分析")
    weak_items = str(latest.get("weak_items", "")).strip()
    if weak_items:
        st.warning(f"当前短板项：{weak_items.replace(',', '、')}")
    else:
        st.info("暂未识别到明显短板项。")

    # =========================
    # 训练建议
    # =========================
    st.subheader("我的训练建议")
    st.markdown(
        f"""
### 建议训练方案

{latest["Recommendation"]}

建议每周保持规律运动，并注意休息恢复。
"""
    )

    st.markdown("### 体质等级说明")
    st.info(
        """
优秀：体质状况良好  
良好：体质达标  
及格：已达到基本要求，但仍有提升空间  
不及格：建议重点关注体能训练与持续干预
"""
    )

    # =========================
    # 体测趋势
    # =========================
    st.subheader("我的体测趋势")

    metric_mapping = {
        "全部指标": None,
        "BMI": "bmi",
        "肺活量": "lung_capacity",
        "50米跑": "sprint_50m",
        "坐位体前屈": "sit_and_reach",
        "立定跳远": "standing_long_jump",
        "耐力跑": "endurance_run",
        "力量项目": "strength",
        "总分": "total_score"
    }

    metric_option = st.selectbox(
        "选择查看指标",
        list(metric_mapping.keys())
    )

    trend_cols = [
        col for col in ["bmi", "lung_capacity", "sprint_50m", "standing_long_jump", "total_score"]
        if col in student_df.columns
    ]

    if metric_option == "全部指标":
        if not trend_cols:
            st.info("暂无可展示的趋势指标。")
        else:
            fig = px.line(
                student_df,
                x="test_date",
                y=trend_cols,
                markers=True,
                title=f"学生 {student_id} 体测指标变化趋势"
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
    else:
        metric_col = metric_mapping[metric_option]
        if metric_col not in student_df.columns:
            st.info(f"当前数据中缺少 {metric_option} 字段。")
        else:
            hover_cols = [
                col for col in [
                    "test_date", "bmi", "lung_capacity", "sprint_50m",
                    "sit_and_reach", "standing_long_jump", "endurance_run",
                    "strength", "total_score", "level", "Recommendation"
                ] if col in student_df.columns
            ]

            hover_data = {col: True for col in hover_cols}

            fig = px.line(
                student_df,
                x="test_date",
                y=metric_col,
                markers=True,
                title=f"学生 {student_id} {metric_option} 变化趋势",
                hover_data=hover_data
            )
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

    # =========================
    # 历史体测记录
    # =========================
    st.subheader("我的历史体测记录")

    show_cols = [
        "test_date", "grade", "gender",
        "height_cm", "weight_kg", "bmi",
        "lung_capacity", "sprint_50m", "sit_and_reach",
        "standing_long_jump", "endurance_run", "strength",
        "total_score", "level", "weak_items", "Recommendation"
    ]
    show_cols = [c for c in show_cols if c in student_df.columns]

    display_df = student_df[show_cols].copy()

    if "level" in display_df.columns:
        display_df["level"] = display_df["level"].apply(level_to_text)

    if "test_date" in display_df.columns:
        display_df["test_date"] = display_df["test_date"].dt.strftime("%Y-%m-%d")

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
        "weak_items": "短板项",
        "Recommendation": "训练建议"
    }
    display_df = display_df.rename(columns=rename_map)

    with st.expander("展开查看详细历史体测数据"):
        st.dataframe(display_df, use_container_width=True)
