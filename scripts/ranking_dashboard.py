import pandas as pd
import streamlit as st

from scripts.db_utils import get_all_exercise_records
from scripts.motivation_utils import (
    get_student_motivation_stats,
    get_student_medals,
    calc_rank_score
)


def _normalize_exercise_df(rows):
    """
    兼容 db_utils.get_all_exercise_records() 返回的字典列表，
    统一整理成排行榜页面使用的字段格式。
    """
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).copy()

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
    df = df.rename(columns=rename_map)

    expected_cols = [
        "StudentID", "姓名", "班级", "运动日期", "运动类型",
        "运动时长(分钟)", "运动强度", "备注", "提交时间"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df["StudentID"] = df["StudentID"].astype(str).str.zfill(3)

    # 关键修复：把运动日期转成 Python date，避免 motivation_utils 内部比较时报错
    df["运动日期"] = pd.to_datetime(df["运动日期"], errors="coerce")
    df = df.dropna(subset=["运动日期"]).copy()
    df["运动日期"] = df["运动日期"].dt.date

    df["运动时长(分钟)"] = pd.to_numeric(df["运动时长(分钟)"], errors="coerce").fillna(0)

    return df


def run_ranking_dashboard():
    st.header("班级运动排行榜与激励统计")
    st.caption("基于家庭运动打卡记录，统计学生运动活跃度、奖牌情况与重点关注对象")

    rows = get_all_exercise_records()

    if not rows:
        st.info("当前还没有家庭运动打卡记录，暂时无法生成排行榜。")
        return

    exercise_df = _normalize_exercise_df(rows)

    if exercise_df.empty:
        st.info("当前还没有家庭运动打卡记录，暂时无法生成排行榜。")
        return

    # =========================
    # 班级筛选
    # =========================
    class_options = ["全部"] + sorted(
        [x for x in exercise_df["班级"].dropna().unique().tolist() if str(x).strip() != ""]
    )
    selected_class = st.selectbox("选择班级", class_options)

    if selected_class != "全部":
        exercise_df = exercise_df[exercise_df["班级"] == selected_class].copy()

    if exercise_df.empty:
        st.warning("当前筛选条件下没有运动记录。")
        return

    # =========================
    # 逐个学生统计
    # =========================
    ranking_records = []
    all_medals_flat = []

    for student_id, group in exercise_df.groupby("StudentID"):
        try:
            stats = get_student_motivation_stats(group.copy())
            medals = get_student_medals(stats)
        except Exception:
            # 防止单个学生数据异常拖垮整个排行榜
            stats = {
                "week_count": 0,
                "week_duration": 0,
                "consecutive_days": 0,
                "total_duration": 0,
                "exercise_type_count": 0
            }
            medals = []

        for medal in medals:
            all_medals_flat.append(medal)

        row = {
            "StudentID": student_id,
            "姓名": group["姓名"].iloc[0] if "姓名" in group.columns and len(group) > 0 else "",
            "班级": group["班级"].iloc[0] if "班级" in group.columns and len(group) > 0 else "",
            "本周打卡次数": stats.get("week_count", 0),
            "本周运动时长": stats.get("week_duration", 0),
            "连续打卡天数": stats.get("consecutive_days", 0),
            "累计运动时长": stats.get("total_duration", 0),
            "运动类型数": stats.get("exercise_type_count", 0),
            "综合积分": calc_rank_score(stats),
            "奖牌数": len(medals),
            "奖牌": " | ".join(medals) if medals else "暂无"
        }
        ranking_records.append(row)

    ranking_df = pd.DataFrame(ranking_records)

    if ranking_df.empty:
        st.warning("暂无可用于排行的数据。")
        return

    # =========================
    # 概览卡片
    # =========================
    st.markdown("### 概览统计")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("参与学生数", ranking_df["StudentID"].nunique())
    c2.metric("本周总打卡次数", int(ranking_df["本周打卡次数"].sum()))
    c3.metric("本周总运动时长", f"{int(ranking_df['本周运动时长'].sum())}分钟")
    c4.metric("已获奖牌总数", int(ranking_df["奖牌数"].sum()))

    # =========================
    # 奖牌统计
    # =========================
    st.markdown("### 奖牌统计")

    if all_medals_flat:
        medal_stat_df = pd.Series(all_medals_flat).value_counts().reset_index()
        medal_stat_df.columns = ["奖牌名称", "获得次数"]
        st.dataframe(medal_stat_df, use_container_width=True)
    else:
        st.info("当前还没有学生解锁奖牌。")

    # =========================
    # 班级运动之星
    # =========================
    st.markdown("### 班级运动之星")

    star_df = ranking_df.sort_values(
        ["综合积分", "本周打卡次数", "本周运动时长"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    top_star = star_df.iloc[0]

    s1, s2, s3 = st.columns(3)
    s1.metric("运动之星", top_star["姓名"])
    s2.metric("综合积分", round(float(top_star["综合积分"]), 1))
    s3.metric("本周打卡次数", int(top_star["本周打卡次数"]))

    st.success(
        f"本周班级运动之星：{top_star['姓名']}（学号 {top_star['StudentID']}），"
        f"累计获得 {top_star['奖牌数']} 枚奖牌。"
    )

    # =========================
    # 低参与预警
    # =========================
    st.markdown("### 低参与预警")

    low_active_df = ranking_df[
        (ranking_df["本周打卡次数"] < 2) | (ranking_df["连续打卡天数"] == 0)
    ].copy()

    if low_active_df.empty:
        st.success("当前没有明显低参与学生。")
    else:
        warn_df = low_active_df[
            ["StudentID", "姓名", "班级", "本周打卡次数", "连续打卡天数", "综合积分"]
        ].sort_values(
            ["本周打卡次数", "连续打卡天数", "综合积分"],
            ascending=[True, True, True]
        )
        st.warning(f"当前识别到 {len(warn_df)} 名低参与学生，建议教师进行激励或提醒。")
        st.dataframe(warn_df, use_container_width=True)

    # =========================
    # 排行榜 tabs
    # =========================
    tab1, tab2, tab3 = st.tabs(["打卡次数榜", "运动时长榜", "综合积分榜"])

    with tab1:
        st.markdown("#### 本周打卡次数榜")
        checkin_rank_df = ranking_df.sort_values(
            ["本周打卡次数", "综合积分"],
            ascending=[False, False]
        ).reset_index(drop=True)
        checkin_rank_df.index = checkin_rank_df.index + 1

        st.dataframe(
            checkin_rank_df[["StudentID", "姓名", "班级", "本周打卡次数", "连续打卡天数", "奖牌数"]],
            use_container_width=True
        )

    with tab2:
        st.markdown("#### 本周运动时长榜")
        duration_rank_df = ranking_df.sort_values(
            ["本周运动时长", "综合积分"],
            ascending=[False, False]
        ).reset_index(drop=True)
        duration_rank_df.index = duration_rank_df.index + 1

        st.dataframe(
            duration_rank_df[["StudentID", "姓名", "班级", "本周运动时长", "本周打卡次数", "奖牌数"]],
            use_container_width=True
        )

    with tab3:
        st.markdown("#### 综合积分榜")
        score_rank_df = ranking_df.sort_values(
            ["综合积分", "本周打卡次数", "本周运动时长"],
            ascending=[False, False, False]
        ).reset_index(drop=True)
        score_rank_df.index = score_rank_df.index + 1

        st.dataframe(
            score_rank_df[
                ["StudentID", "姓名", "班级", "综合积分", "本周打卡次数", "本周运动时长", "连续打卡天数", "奖牌数"]
            ],
            use_container_width=True
        )

    # =========================
    # 详细激励数据
    # =========================
    st.markdown("### 学生激励详情")
    st.dataframe(
        ranking_df[
            ["StudentID", "姓名", "班级", "奖牌数", "奖牌", "综合积分", "本周打卡次数", "连续打卡天数"]
        ].sort_values(["综合积分", "奖牌数"], ascending=[False, False]),
        use_container_width=True
    )

    # =========================
    # 导出 CSV
    # =========================
    csv_data = ranking_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下载排行榜与奖牌统计 CSV",
        csv_data,
        "班级运动排行榜_奖牌统计.csv",
        "text/csv"
    )
