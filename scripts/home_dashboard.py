import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st
import joblib

from scripts.db_utils import get_all_exercise_records
from scripts.motivation_utils import (
    get_student_motivation_stats,
    get_student_medals,
    calc_rank_score
)


# =========================
# 移动端样式
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
    .featured-video-card {
        background: #fcfdff;
        border: 1px solid #e1ecf4;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    </style>
    """, unsafe_allow_html=True)


def _normalize_exercise_df(exercise_rows):
    """
    把数据库返回的运动记录统一整理成首页可用格式。
    """
    if not exercise_rows:
        return pd.DataFrame()

    exercise_df = pd.DataFrame(exercise_rows).copy()

    rename_map = {
        "id": "记录ID",
        "student_id": "StudentID",
        "name": "姓名",
        "class_name": "班级",
        "exercise_date": "运动日期",
        "exercise_type": "运动类型",
        "duration_minutes": "运动时长(分钟)",
        "intensity": "运动强度",
        "remark": "备注",
        "created_at": "提交时间",
        "video_path": "视频路径",
        "video_filename": "视频文件名",
        "teacher_feedback": "教师反馈",
        "teacher_rating": "教师评价",
        "teacher_feedback_at": "反馈时间",
        "review_status": "反馈状态",
        "is_featured": "是否优秀视频"
    }

    exercise_df = exercise_df.rename(columns=rename_map)

    expected_cols = [
        "记录ID", "StudentID", "姓名", "班级", "运动日期", "运动类型",
        "运动时长(分钟)", "运动强度", "备注", "提交时间",
        "视频路径", "视频文件名", "教师反馈", "教师评价",
        "反馈时间", "反馈状态", "是否优秀视频"
    ]
    for col in expected_cols:
        if col not in exercise_df.columns:
            exercise_df[col] = None

    exercise_df["StudentID"] = exercise_df["StudentID"].astype(str).str.zfill(3)

    exercise_df["运动日期"] = pd.to_datetime(exercise_df["运动日期"], errors="coerce")
    exercise_df["提交时间"] = pd.to_datetime(exercise_df["提交时间"], errors="coerce")
    exercise_df = exercise_df.dropna(subset=["运动日期"]).copy()
    exercise_df["运动日期_date"] = exercise_df["运动日期"].dt.date

    exercise_df["运动时长(分钟)"] = pd.to_numeric(
        exercise_df["运动时长(分钟)"], errors="coerce"
    ).fillna(0)

    exercise_df["是否优秀视频"] = pd.to_numeric(
        exercise_df["是否优秀视频"], errors="coerce"
    ).fillna(0).astype(int)

    return exercise_df


def _render_featured_videos(featured_df):
    """首页优秀视频展示区"""
    st.markdown("### 本周优秀视频展示")

    if featured_df.empty:
        st.info("本周还没有被教师标记为优秀的视频。")
        return

    st.caption("展示最近被教师标记为优秀的学生运动视频，可用于班级示范与激励。")

    preview_df = featured_df.head(3).copy()

    for _, row in preview_df.iterrows():
        title = (
            f"{row['姓名']}｜{row['班级']}｜"
            f"{row['运动日期'].strftime('%Y-%m-%d') if pd.notna(row['运动日期']) else '-'}｜"
            f"{row['运动类型']}"
        )

        st.markdown(
            f"""
            <div class="featured-video-card">
                <b>🌟 {title}</b>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write(f"**学号：** {row['StudentID']}")
        st.write(f"**运动时长：** {int(row['运动时长(分钟)'])} 分钟")
        st.write(f"**教师评价：** {row['教师评价'] if pd.notna(row['教师评价']) else '未评价'}")

        if pd.notna(row["教师反馈"]) and str(row["教师反馈"]).strip():
            st.info(f"教师反馈：{row['教师反馈']}")

        video_path = row["视频路径"]
        if pd.notna(video_path) and str(video_path).strip():
            try:
                if os.path.exists(video_path):
                    with open(video_path, "rb") as f:
                        st.video(f.read())
                else:
                    st.warning("视频文件未找到。")
            except Exception as e:
                st.warning(f"视频加载失败：{e}")

    if len(featured_df) > 3:
        with st.expander("查看更多优秀视频"):
            more_df = featured_df.iloc[3:].copy()

            for _, row in more_df.iterrows():
                st.markdown(
                    f"**🌟 {row['姓名']}｜{row['班级']}｜"
                    f"{row['运动日期'].strftime('%Y-%m-%d') if pd.notna(row['运动日期']) else '-'}｜"
                    f"{row['运动类型']}**"
                )
                st.write(f"学号：{row['StudentID']}｜运动时长：{int(row['运动时长(分钟)'])} 分钟")
                st.write(f"教师评价：{row['教师评价'] if pd.notna(row['教师评价']) else '未评价'}")

                if pd.notna(row["教师反馈"]) and str(row["教师反馈"]).strip():
                    st.caption(f"教师反馈：{row['教师反馈']}")

                video_path = row["视频路径"]
                if pd.notna(video_path) and str(video_path).strip():
                    try:
                        if os.path.exists(video_path):
                            with open(video_path, "rb") as f:
                                st.video(f.read())
                        else:
                            st.warning("视频文件未找到。")
                    except Exception as e:
                        st.warning(f"视频加载失败：{e}")

                st.markdown("---")


def run_home_dashboard():
    apply_mobile_style()

    script_dir = os.path.dirname(__file__)
    csv_path = os.path.join(script_dir, "../data/students.csv")
    risk_model_path = os.path.join(script_dir, "../models/risk_predict_model.pkl")

    if not os.path.exists(csv_path):
        st.warning("未找到 students.csv，请先准备数据。")
        return

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        st.error(f"读取 students.csv 失败：{e}")
        return

    if "Date" not in df.columns or "StudentID" not in df.columns:
        st.warning("students.csv 缺少必要列：Date 或 StudentID")
        return

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)
    df = df.dropna(subset=["Date"]).copy()

    numeric_cols = [
        "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "Label" not in df.columns:
        df["Label"] = 1

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

    df["RiskFlag"] = df.apply(identify_risk, axis=1)
    df["NeedAttention"] = df["RiskFlag"].apply(lambda x: 0 if x == "正常" else 1)
    df["WeekStr"] = df["Date"].dt.strftime("%Y-%m-%d")

    latest_df = (
        df.sort_values("Date")
        .groupby("StudentID", as_index=False)
        .tail(1)
        .copy()
    )

    class_score = round(100 - latest_df["Label"].fillna(1).mean() * 20, 1)

    st.markdown(
        """
        <div class="mobile-card">
            <div class="mobile-title">教师端首页总览</div>
            <div class="mobile-sub">整合班级体测、家庭运动、视频打卡、奖牌激励与风险预警数据，帮助教师快速掌握学生状态。</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # =========================
    # 1. 本周总览
    # =========================
    st.markdown("### 本周总览")

    risk_count = int(latest_df["NeedAttention"].sum())
    student_count = latest_df["StudentID"].nunique()

    c1, c2, c3 = st.columns(3)
    c1.metric("学生总数", student_count)
    c2.metric("重点关注人数", risk_count)
    c3.metric("班级体质评分", class_score)

    # =========================
    # 2. 家庭运动与奖牌统计
    # =========================
    st.markdown("### 家庭运动与奖牌概览")

    exercise_rows = get_all_exercise_records()
    ranking_df = pd.DataFrame()
    all_medals_flat = []
    featured_this_week_df = pd.DataFrame()

    if exercise_rows:
        exercise_df = _normalize_exercise_df(exercise_rows)

        if not exercise_df.empty:
            active_student_count = exercise_df["StudentID"].nunique()
            total_exercise_count = len(exercise_df)

            today = date.today()
            week_start = today - timedelta(days=today.weekday())
            week_end = today

            week_df = exercise_df[
                (exercise_df["运动日期_date"] >= week_start) &
                (exercise_df["运动日期_date"] <= week_end)
            ].copy()

            weekly_video_count = int(
                (
                    week_df["视频路径"].notna() &
                    (week_df["视频路径"].astype(str).str.strip() != "")
                ).sum()
            ) if not week_df.empty else 0

            weekly_video_students = int(
                week_df[
                    week_df["视频路径"].notna() &
                    (week_df["视频路径"].astype(str).str.strip() != "")
                ]["StudentID"].nunique()
            ) if not week_df.empty else 0

            weekly_featured_count = int(
                (week_df["是否优秀视频"].fillna(0).astype(int) == 1).sum()
            ) if not week_df.empty else 0

            featured_this_week_df = week_df[
                (week_df["是否优秀视频"].fillna(0).astype(int) == 1) &
                week_df["视频路径"].notna() &
                (week_df["视频路径"].astype(str).str.strip() != "")
            ].copy()

            featured_this_week_df = featured_this_week_df.sort_values(
                ["运动日期", "提交时间"],
                ascending=[False, False]
            )

            rank_records = []
            for student_id, group in exercise_df.groupby("StudentID"):
                try:
                    stats = get_student_motivation_stats(group.copy())
                    medals = get_student_medals(stats)
                except Exception:
                    stats = {
                        "week_count": 0,
                        "week_duration": 0,
                        "consecutive_days": 0,
                        "total_duration": 0,
                        "exercise_type_count": 0,
                        "video_count": 0,
                        "excellent_video_count": 0
                    }
                    medals = []

                for medal in medals:
                    all_medals_flat.append(medal)

                rank_records.append({
                    "StudentID": student_id,
                    "姓名": group["姓名"].iloc[0] if len(group) > 0 else "",
                    "班级": group["班级"].iloc[0] if len(group) > 0 else "",
                    "本周打卡次数": stats.get("week_count", 0),
                    "本周运动时长": stats.get("week_duration", 0),
                    "连续打卡天数": stats.get("consecutive_days", 0),
                    "综合积分": calc_rank_score(stats),
                    "奖牌数": len(medals),
                    "奖牌": " | ".join(medals) if medals else "暂无"
                })

            ranking_df = pd.DataFrame(rank_records)

            low_active_count = 0
            if not ranking_df.empty:
                low_active_count = int(
                    ((ranking_df["本周打卡次数"] < 2) | (ranking_df["连续打卡天数"] == 0)).sum()
                )

            d1, d2 = st.columns(2)
            d1.metric("参与打卡学生数", active_student_count)
            d2.metric("低活跃学生数", low_active_count)

            d3, d4 = st.columns(2)
            d3.metric("家庭运动总记录数", total_exercise_count)
            d4.metric("奖牌总数", int(ranking_df["奖牌数"].sum()) if not ranking_df.empty else 0)

            d5, d6 = st.columns(2)
            d5.metric("本周视频打卡人数", weekly_video_students)
            d6.metric("本周优秀视频数", weekly_featured_count)

            if not ranking_df.empty:
                top_star_df = ranking_df.sort_values(
                    ["综合积分", "本周打卡次数", "本周运动时长"],
                    ascending=[False, False, False]
                ).reset_index(drop=True)

                top_star_name = top_star_df.iloc[0]["姓名"]
                top_star_score = round(float(top_star_df.iloc[0]["综合积分"]), 1)

                st.success(f"本周运动之星：{top_star_name}（综合积分 {top_star_score} 分）")

            if weekly_video_count > 0:
                st.info(f"本周共收到 {weekly_video_count} 条视频打卡记录，其中 {weekly_featured_count} 条已被标记为优秀视频。")
        else:
            st.info("当前暂无可用的家庭运动打卡数据。")
    else:
        st.info("当前暂无家庭运动打卡数据。")

    # =========================
    # 3. 本周优秀视频展示
    # =========================
    _render_featured_videos(featured_this_week_df)

    # =========================
    # 4. AI 风险预测概览
    # =========================
    st.markdown("### AI 风险预测概览")

    risk_feature_cols = [
        "BMI", "LungCapacity", "Run50m", "Jump",
        "Label", "CardioLabel", "SpeedLabel", "StrengthLabel"
    ]

    if os.path.exists(risk_model_path):
        try:
            missing_cols = [c for c in risk_feature_cols if c not in latest_df.columns]
            if missing_cols:
                st.warning(f"风险预测缺少字段：{', '.join(missing_cols)}")
            else:
                risk_input_df = latest_df[risk_feature_cols].copy()
                risk_input_df = risk_input_df.fillna(risk_input_df.median(numeric_only=True))
                risk_input_df = risk_input_df.fillna(0)

                risk_model = joblib.load(risk_model_path)

                risk_pred = risk_model.predict(risk_input_df)
                risk_prob = risk_model.predict_proba(risk_input_df)[:, 1]

                latest_df["PredRisk"] = risk_pred
                latest_df["RiskProb"] = risk_prob

                high_risk_df = latest_df[latest_df["PredRisk"] == 1].copy()
                high_risk_df = high_risk_df.sort_values("RiskProb", ascending=False)

                pred_risk_count = len(high_risk_df)
                pred_risk_ratio = round(pred_risk_count / len(latest_df) * 100, 1) if len(latest_df) > 0 else 0

                r1, r2 = st.columns(2)
                r1.metric("预测高风险人数", pred_risk_count)
                r2.metric("预测风险占比", f"{pred_risk_ratio}%")

                if not high_risk_df.empty:
                    st.warning("以下学生下一次可能需要重点关注。")
                    preview_df = high_risk_df[[
                        "StudentID", "RiskFlag", "RiskProb"
                    ]].rename(columns={
                        "StudentID": "学号",
                        "RiskFlag": "当前风险",
                        "RiskProb": "风险概率"
                    }).head(5)

                    st.dataframe(
                        preview_df.style.background_gradient(subset=["风险概率"], cmap="Reds"),
                        use_container_width=True
                    )

                    with st.expander("展开查看全部预测高风险学生"):
                        full_df = high_risk_df[[
                            "StudentID", "BMI", "LungCapacity", "Run50m",
                            "Jump", "Label", "RiskFlag", "RiskProb"
                        ]].rename(columns={
                            "StudentID": "学号",
                            "BMI": "BMI",
                            "LungCapacity": "肺活量",
                            "Run50m": "50米跑",
                            "Jump": "跳远",
                            "Label": "等级",
                            "RiskFlag": "当前风险",
                            "RiskProb": "风险概率"
                        })
                        st.dataframe(
                            full_df.style.background_gradient(subset=["风险概率"], cmap="Reds"),
                            use_container_width=True
                        )
                else:
                    st.success("当前暂无明显新增风险学生。")

        except Exception as e:
            st.error(f"AI风险预测加载失败：{e}")
    else:
        st.info("尚未训练风险预测模型，请先运行 scripts/train_risk_model.py")

    # =========================
    # 5. 排行榜速览
    # =========================
    st.markdown("### 排行榜速览")

    if not ranking_df.empty:
        top5_df = ranking_df.sort_values(
            ["综合积分", "本周打卡次数", "本周运动时长"],
            ascending=[False, False, False]
        ).head(5)[["StudentID", "姓名", "综合积分", "奖牌数"]]

        st.dataframe(top5_df, use_container_width=True)
    else:
        st.info("当前暂无可展示的排行榜数据。")

    # =========================
    # 6. 图表概览
    # =========================
    st.markdown("### 班级图表概览")

    metric_option = st.selectbox(
        "选择首页展示指标",
        ["BMI", "LungCapacity", "Run50m", "Jump", "Label"],
        index=0,
        key="home_metric_option"
    )

    week_group = (
        df.groupby("WeekStr", as_index=False)[metric_option]
        .mean()
        .sort_values("WeekStr")
    )

    fig = px.line(
        week_group,
        x="WeekStr",
        y=metric_option,
        markers=True,
        title=f"{metric_option} 班级周度平均变化"
    )

    if metric_option == "Label":
        fig.update_layout(
            yaxis=dict(
                tickvals=[0, 1, 2, 3],
                ticktext=["优秀", "良好", "中等", "差"]
            )
        )

    fig.update_layout(
        xaxis_title="日期",
        yaxis_title=metric_option,
        height=320
    )
    st.plotly_chart(fig, use_container_width=True)

    label_map = {0: "优秀", 1: "良好", 2: "中等", 3: "差"}
    label_dist = latest_df["Label"].map(label_map).value_counts().reset_index()
    label_dist.columns = ["体质等级", "人数"]

    label_fig = px.bar(
        label_dist,
        x="体质等级",
        y="人数",
        title="最新体质等级分布"
    )
    label_fig.update_layout(height=320)
    st.plotly_chart(label_fig, use_container_width=True)

    if exercise_rows:
        exercise_df = _normalize_exercise_df(exercise_rows)

        if not exercise_df.empty:
            exercise_type_stat = exercise_df["运动类型"].value_counts().reset_index()
            exercise_type_stat.columns = ["运动类型", "次数"]

            exercise_fig = px.bar(
                exercise_type_stat,
                x="运动类型",
                y="次数",
                title="家庭运动类型统计"
            )
            exercise_fig.update_layout(height=320)
            st.plotly_chart(exercise_fig, use_container_width=True)

            if all_medals_flat:
                medal_stat_df = pd.Series(all_medals_flat).value_counts().reset_index()
                medal_stat_df.columns = ["奖牌名称", "获得次数"]

                medal_fig = px.bar(
                    medal_stat_df,
                    x="奖牌名称",
                    y="获得次数",
                    title="奖牌获得情况统计"
                )
                medal_fig.update_layout(height=320)
                st.plotly_chart(medal_fig, use_container_width=True)

            video_stat_df = pd.DataFrame({
                "类型": ["普通打卡", "视频打卡"],
                "数量": [
                    int(
                        (
                            exercise_df["视频路径"].isna() |
                            (exercise_df["视频路径"].astype(str).str.strip() == "")
                        ).sum()
                    ),
                    int(
                        (
                            exercise_df["视频路径"].notna() &
                            (exercise_df["视频路径"].astype(str).str.strip() != "")
                        ).sum()
                    )
                ]
            })

            video_fig = px.bar(
                video_stat_df,
                x="类型",
                y="数量",
                title="普通打卡 / 视频打卡对比"
            )
            video_fig.update_layout(height=320)
            st.plotly_chart(video_fig, use_container_width=True)

    # =========================
    # 7. 重点关注学生
    # =========================
    st.markdown("### 重点关注学生")

    risk_students = latest_df[latest_df["RiskFlag"] != "正常"].copy()

    if risk_students.empty:
        st.success("当前暂无重点关注学生。")
    else:
        preview_cols = ["StudentID", "RiskFlag"]
        preview_df = risk_students[preview_cols].rename(columns={
            "StudentID": "学号",
            "RiskFlag": "风险类型"
        }).head(5)

        st.dataframe(preview_df, use_container_width=True)

        with st.expander("展开查看全部重点关注学生"):
            show_cols = [
                "StudentID", "Date", "BMI", "LungCapacity",
                "Run50m", "Jump", "Label", "RiskFlag"
            ]
            full_df = risk_students[show_cols].sort_values("StudentID").rename(columns={
                "StudentID": "学号",
                "Date": "日期",
                "BMI": "BMI",
                "LungCapacity": "肺活量",
                "Run50m": "50米跑",
                "Jump": "跳远",
                "Label": "等级",
                "RiskFlag": "风险类型"
            })
            st.dataframe(full_df, use_container_width=True)

    # =========================
    # 8. 系统说明
    # =========================
    with st.expander("查看系统功能说明"):
        st.markdown(
            """
            - **教师端**：查看班级分析、风险学生、数据管理、学生信息、家庭运动记录、视频反馈、排行榜与重点干预名单  
            - **学生端**：查看个人体测档案、趋势变化、训练建议、家庭运动打卡、视频打卡、奖牌、排名与成长反馈  
            - **AI模块**：支持体质等级预测、风险预警与个性化训练建议  
            - **激励机制**：支持打卡记录、视频打卡、优秀视频展示、奖牌激励、班级排行榜与运动之星展示
            """
        )
