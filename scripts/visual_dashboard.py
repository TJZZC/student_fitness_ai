import os
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# =========================
# 标签映射
# =========================
label_text_map = ["优秀", "良好", "中等", "差"]


# =========================
# 页面样式（移动端优化）
# =========================
def apply_mobile_style():
    st.markdown("""
    <style>
    .mobile-card {
        background-color: #f8fbff;
        border: 1px solid #d9e8f5;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 12px;
    }
    .mobile-title {
        font-size: 18px;
        font-weight: 700;
        color: #1f4e79;
        margin-bottom: 8px;
    }
    .mobile-sub {
        color: #666;
        font-size: 14px;
        margin-bottom: 4px;
    }
    </style>
    """, unsafe_allow_html=True)


# =========================
# AI 多标签训练函数
# =========================
@st.cache_resource
def train_multi_models(dataframe):
    dataframe = dataframe.sort_values(["StudentID", "Date"]).reset_index(drop=True)
    window_size = 3
    targets = ["Label", "CardioLabel", "SpeedLabel", "StrengthLabel"]

    X = []
    y_dict = {t: [] for t in targets}

    for student_id, group in dataframe.groupby("StudentID"):
        group = group.sort_values("Date").reset_index(drop=True)

        if len(group) <= window_size:
            continue

        for i in range(len(group) - window_size):
            history = group.iloc[i:i + window_size]
            target = group.iloc[i + window_size]

            features = []
            for _, row in history.iterrows():
                features.extend([
                    row["BMI"],
                    row["LungCapacity"],
                    row["Run50m"],
                    row["Jump"],
                    row["Label"],
                    row["CardioLabel"],
                    row["SpeedLabel"],
                    row["StrengthLabel"]
                ])

            features.extend([
                history["BMI"].mean(),
                history["LungCapacity"].mean(),
                history["Run50m"].mean(),
                history["Jump"].mean(),
                history["Label"].mean(),
                history["CardioLabel"].mean(),
                history["SpeedLabel"].mean(),
                history["StrengthLabel"].mean(),

                history.iloc[-1]["BMI"] - history.iloc[0]["BMI"],
                history.iloc[-1]["LungCapacity"] - history.iloc[0]["LungCapacity"],
                history.iloc[-1]["Run50m"] - history.iloc[0]["Run50m"],
                history.iloc[-1]["Jump"] - history.iloc[0]["Jump"],

                history.iloc[-1]["Label"] - history.iloc[0]["Label"],
                history.iloc[-1]["CardioLabel"] - history.iloc[0]["CardioLabel"],
                history.iloc[-1]["SpeedLabel"] - history.iloc[0]["SpeedLabel"],
                history.iloc[-1]["StrengthLabel"] - history.iloc[0]["StrengthLabel"],
            ])

            X.append(features)
            for t in targets:
                y_dict[t].append(target[t])

    if len(X) == 0:
        return None, "样本不足，无法训练预测模型。"

    X = np.array(X)
    for t in targets:
        y_dict[t] = np.array(y_dict[t])

    indices = np.arange(len(X))
    train_idx, _ = train_test_split(indices, test_size=0.2, random_state=42)
    X_train = X[train_idx]

    models = {}
    for t in targets:
        y_train = y_dict[t][train_idx]
        model = RandomForestClassifier(
            n_estimators=120,
            random_state=42,
            max_depth=6
        )
        model.fit(X_train, y_train)
        models[t] = model

    return models, "训练成功"


# =========================
# 趋势分析
# =========================
def analyze_trend(history_df):
    trend = {}

    if len(history_df) < 2:
        trend["CardioTrend"] = "稳定"
        trend["SpeedTrend"] = "稳定"
        trend["StrengthTrend"] = "稳定"
        trend["OverallTrend"] = "稳定"
        return trend

    lung_diff = history_df.iloc[-1]["LungCapacity"] - history_df.iloc[0]["LungCapacity"]
    trend["CardioTrend"] = "改善" if lung_diff > 50 else "下降" if lung_diff < -50 else "稳定"

    run_diff = history_df.iloc[-1]["Run50m"] - history_df.iloc[0]["Run50m"]
    trend["SpeedTrend"] = "改善" if run_diff < -0.05 else "下降" if run_diff > 0.05 else "稳定"

    jump_diff = history_df.iloc[-1]["Jump"] - history_df.iloc[0]["Jump"]
    trend["StrengthTrend"] = "改善" if jump_diff > 3 else "下降" if jump_diff < -3 else "稳定"

    label_diff = history_df.iloc[-1]["Label"] - history_df.iloc[0]["Label"]
    trend["OverallTrend"] = "改善" if label_diff < 0 else "下降" if label_diff > 0 else "稳定"

    return trend


# =========================
# 个性化训练建议
# =========================
def generate_personalized_plan(pred_result, trend_result):
    advice_lines = []
    weekly_plan = []

    overall = pred_result["Label"]
    cardio = pred_result["CardioLabel"]
    speed = pred_result["SpeedLabel"]
    strength = pred_result["StrengthLabel"]

    advice_lines.append(f"预测下一次综合体质等级：{label_text_map[overall]}")
    advice_lines.append(
        f"分项预测：心肺{label_text_map[cardio]}，速度{label_text_map[speed]}，力量{label_text_map[strength]}"
    )
    advice_lines.append(
        f"趋势判断：综合{trend_result['OverallTrend']}，心肺{trend_result['CardioTrend']}，速度{trend_result['SpeedTrend']}，力量{trend_result['StrengthTrend']}"
    )

    weak_items = []
    if cardio >= 2:
        weak_items.append("心肺")
    if speed >= 2:
        weak_items.append("速度")
    if strength >= 2:
        weak_items.append("力量")

    if not weak_items:
        advice_lines.append("整体状态较好，建议保持当前训练节奏，并适当增加综合体能训练。")
        weekly_plan.extend([
            "每周2次耐力跑（15~20分钟）",
            "每周2次短距离加速跑训练",
            "每周2次下肢力量与核心稳定训练"
        ])
    else:
        advice_lines.append("当前重点短板：" + "、".join(weak_items))

        if "心肺" in weak_items:
            advice_lines.append("建议加强有氧耐力训练，提高肺活量与持续运动能力。")
            weekly_plan.extend([
                "每周3次中低强度慢跑，每次15~25分钟",
                "每周1~2次间歇跑（如200米×4组）"
            ])

        if "速度" in weak_items:
            advice_lines.append("建议加强起跑反应、步频和短距离冲刺训练。")
            weekly_plan.extend([
                "每周2次30米~50米加速跑训练",
                "每周2次高抬腿、后蹬跑等跑姿专项练习"
            ])

        if "力量" in weak_items:
            advice_lines.append("建议加强下肢爆发力和核心力量训练。")
            weekly_plan.extend([
                "每周2次跳跃训练（原地纵跳、连续跳）",
                "每周2次深蹲、弓步蹲、平板支撑训练"
            ])

    if trend_result["OverallTrend"] == "下降":
        advice_lines.append("最近整体趋势有下降，建议适当增加训练规律性，并关注恢复和睡眠。")
    elif trend_result["OverallTrend"] == "改善":
        advice_lines.append("最近整体趋势在改善，建议保持训练连续性。")

    weekly_plan = list(dict.fromkeys(weekly_plan))
    return advice_lines, weekly_plan


# =========================
# AI 预测函数
# =========================
def predict_and_advise(student_id, dataframe, models):
    if models is None:
        return None, "模型未成功训练。"

    window_size = 3
    student_df = dataframe[dataframe["StudentID"] == student_id].sort_values("Date").reset_index(drop=True)

    if len(student_df) < window_size:
        return None, "该学生历史记录不足，无法预测。"

    history = student_df.iloc[-window_size:]

    features = []
    for _, row in history.iterrows():
        features.extend([
            row["BMI"],
            row["LungCapacity"],
            row["Run50m"],
            row["Jump"],
            row["Label"],
            row["CardioLabel"],
            row["SpeedLabel"],
            row["StrengthLabel"]
        ])

    features.extend([
        history["BMI"].mean(),
        history["LungCapacity"].mean(),
        history["Run50m"].mean(),
        history["Jump"].mean(),
        history["Label"].mean(),
        history["CardioLabel"].mean(),
        history["SpeedLabel"].mean(),
        history["StrengthLabel"].mean(),

        history.iloc[-1]["BMI"] - history.iloc[0]["BMI"],
        history.iloc[-1]["LungCapacity"] - history.iloc[0]["LungCapacity"],
        history.iloc[-1]["Run50m"] - history.iloc[0]["Run50m"],
        history.iloc[-1]["Jump"] - history.iloc[0]["Jump"],

        history.iloc[-1]["Label"] - history.iloc[0]["Label"],
        history.iloc[-1]["CardioLabel"] - history.iloc[0]["CardioLabel"],
        history.iloc[-1]["SpeedLabel"] - history.iloc[0]["SpeedLabel"],
        history.iloc[-1]["StrengthLabel"] - history.iloc[0]["StrengthLabel"],
    ])

    pred_result = {}
    for t, model in models.items():
        pred_result[t] = int(model.predict([features])[0])

    trend_result = analyze_trend(history)
    advice_lines, weekly_plan = generate_personalized_plan(pred_result, trend_result)

    return {
        "pred_result": pred_result,
        "trend_result": trend_result,
        "advice_lines": advice_lines,
        "weekly_plan": weekly_plan
    }, "预测成功"


# =========================
# 页面主函数
# =========================
def run_dashboard():
    apply_mobile_style()

    st.markdown(
        """
        <div class="mobile-card">
            <div class="mobile-title">班级分析与AI预测</div>
            <div class="mobile-sub">面向教师展示班级整体情况、学生个体趋势、AI预测与训练建议。</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    script_dir = os.path.dirname(__file__)
    csv_path = os.path.join(script_dir, "../data/students.csv")

    if not os.path.exists(csv_path):
        st.error(f"未找到数据文件：{csv_path}")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"读取数据失败：{e}")
        return

    required_cols = [
        "StudentID", "Date", "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]
    missing_cols = [c for c in required_cols if c not in df.columns]
    if missing_cols:
        st.error(f"students.csv 缺少必要列：{missing_cols}")
        return

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)
    df = df.dropna(subset=["Date"]).copy()

    latest_df = (
        df.sort_values("Date")
        .groupby("StudentID", as_index=False)
        .tail(1)
        .copy()
    )

    # =========================
    # 班级概览
    # =========================
    st.markdown("### 班级概览")

    c1, c2 = st.columns(2)
    c1.metric("学生总数", latest_df["StudentID"].nunique())
    c2.metric("平均 BMI", round(latest_df["BMI"].mean(), 2))

    c3, c4 = st.columns(2)
    c3.metric("平均肺活量", round(latest_df["LungCapacity"].mean(), 1))
    c4.metric("平均50米跑", round(latest_df["Run50m"].mean(), 2))

    c5, c6 = st.columns(2)
    c5.metric("平均跳远", round(latest_df["Jump"].mean(), 1))
    c6.metric("平均等级", round(latest_df["Label"].mean(), 2))

    # =========================
    # 学生选择
    # =========================
    st.markdown("### 学生个人分析")

    student_list = sorted(df["StudentID"].unique().tolist())
    panel_student = st.selectbox("选择学生", options=student_list, key="panel_student")
    panel_df = df[df["StudentID"] == panel_student].sort_values("Date").copy()
    panel_latest = panel_df.iloc[-1]

    s1, s2 = st.columns(2)
    s1.metric("学生编号", panel_student)
    s2.metric("BMI", round(panel_latest["BMI"], 2))

    s3, s4 = st.columns(2)
    s3.metric("肺活量", round(panel_latest["LungCapacity"], 1))
    s4.metric("50米跑", round(panel_latest["Run50m"], 2))

    s5, _ = st.columns(2)
    s5.metric("立定跳远", round(panel_latest["Jump"], 1))

    # =========================
    # 学生趋势图（单图优先）
    # =========================
    st.markdown("### 学生趋势图")

    metric_option = st.selectbox(
        "选择学生体测指标",
        ["BMI", "LungCapacity", "Run50m", "Jump", "Label"],
        key="student_metric_option"
    )

    fig = px.line(
        panel_df,
        x="Date",
        y=metric_option,
        markers=True,
        title=f"{metric_option} 历史变化趋势"
    )

    if metric_option == "Label":
        fig.update_layout(
            yaxis=dict(
                tickvals=[0, 1, 2, 3],
                ticktext=["优秀", "良好", "中等", "差"]
            )
        )

    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # 雷达图（折叠）
    # =========================
    with st.expander("查看学生雷达图"):
        radar_categories = ["BMI", "LungCapacity", "Run50m表现", "Jump"]
        bmi_value = panel_latest["BMI"]
        lung_value = panel_latest["LungCapacity"] / 100
        run_value = max(0, 15 - panel_latest["Run50m"])
        jump_value = panel_latest["Jump"] / 10
        radar_values = [bmi_value, lung_value, run_value, jump_value]

        radar_fig = go.Figure()
        radar_fig.add_trace(go.Scatterpolar(
            r=radar_values,
            theta=radar_categories,
            fill="toself",
            name=f"学生 {panel_student}"
        ))
        radar_fig.update_layout(
            polar=dict(radialaxis=dict(visible=True)),
            title=f"学生 {panel_student} 最新体测雷达图",
            height=320
        )
        st.plotly_chart(radar_fig, use_container_width=True)

    # =========================
    # AI 预测
    # =========================
    st.markdown("### AI 体质预测与训练建议")

    models, model_status = train_multi_models(df)
    st.caption(f"模型状态：{model_status}")

    ai_result, ai_msg = predict_and_advise(panel_student, df, models)

    if ai_result is None:
        st.warning(ai_msg)
    else:
        pred = ai_result["pred_result"]
        trend = ai_result["trend_result"]

        a1, a2 = st.columns(2)
        a1.metric("综合预测", label_text_map[pred["Label"]])
        a2.metric("综合趋势", trend["OverallTrend"])

        a3, a4 = st.columns(2)
        a3.metric("心肺预测", label_text_map[pred["CardioLabel"]])
        a4.metric("心肺趋势", trend["CardioTrend"])

        a5, a6 = st.columns(2)
        a5.metric("速度预测", label_text_map[pred["SpeedLabel"]])
        a6.metric("速度趋势", trend["SpeedTrend"])

        a7, a8 = st.columns(2)
        a7.metric("力量预测", label_text_map[pred["StrengthLabel"]])
        a8.metric("力量趋势", trend["StrengthTrend"])

        st.markdown("#### 训练建议")
        for line in ai_result["advice_lines"]:
            st.write("•", line)

        with st.expander("查看每周训练计划"):
            for item in ai_result["weekly_plan"]:
                st.write("✓", item)

    # =========================
    # 班级趋势图（折叠）
    # =========================
    with st.expander("查看班级总体趋势"):
        class_metric = st.selectbox(
            "选择班级趋势指标",
            ["BMI", "LungCapacity", "Run50m", "Jump", "Label"],
            key="class_metric_option"
        )

        week_group = (
            df.groupby("Date", as_index=False)[class_metric]
            .mean()
            .sort_values("Date")
        )

        class_fig = px.line(
            week_group,
            x="Date",
            y=class_metric,
            markers=True,
            title=f"{class_metric} 班级总体变化趋势"
        )

        if class_metric == "Label":
            class_fig.update_layout(
                yaxis=dict(
                    tickvals=[0, 1, 2, 3],
                    ticktext=["优秀", "良好", "中等", "差"]
                )
            )

        class_fig.update_layout(height=320)
        st.plotly_chart(class_fig, use_container_width=True)

    # =========================
    # 数据表（折叠）
    # =========================
    with st.expander("查看班级详细数据"):
        show_cols = [
            "StudentID", "Date", "BMI", "LungCapacity", "Run50m", "Jump",
            "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
        ]
        existing_cols = [c for c in show_cols if c in df.columns]
        st.dataframe(
            df[existing_cols].sort_values(["StudentID", "Date"]),
            use_container_width=True
        )
