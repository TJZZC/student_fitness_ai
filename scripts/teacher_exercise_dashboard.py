import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from scripts.db_utils import (
    get_all_exercise_records,
    update_teacher_feedback,
    delete_exercise_record_by_id
)


def normalize_records(rows):
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).copy()

    rename_map = {
        "id": "记录ID",
        "student_id": "学号",
        "name": "姓名",
        "class_name": "班级",
        "gender": "性别",
        "age": "年龄",
        "phone": "电话",
        "exercise_date": "运动日期",
        "exercise_type": "运动类型",
        "duration_minutes": "运动时长(分钟)",
        "intensity": "运动强度",
        "remark": "备注",
        "created_at": "提交时间",
        "video_path": "视频路径",
        "video_filename": "视频文件名",
        "upload_type": "上传类型",
        "teacher_feedback": "教师反馈",
        "teacher_rating": "教师评价",
        "teacher_feedback_at": "反馈时间",
        "review_status": "反馈状态",
        "is_featured": "是否优秀视频"
    }
    df = df.rename(columns=rename_map)

    expected_cols = [
        "记录ID", "学号", "姓名", "班级", "性别", "年龄", "电话",
        "运动日期", "运动类型", "运动时长(分钟)", "运动强度", "备注", "提交时间",
        "视频路径", "视频文件名", "上传类型",
        "教师反馈", "教师评价", "反馈时间", "反馈状态", "是否优秀视频"
    ]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None

    df["学号"] = df["学号"].astype(str).str.zfill(3)
    df["运动日期"] = pd.to_datetime(df["运动日期"], errors="coerce")
    df["提交时间"] = pd.to_datetime(df["提交时间"], errors="coerce")
    df["运动时长(分钟)"] = pd.to_numeric(df["运动时长(分钟)"], errors="coerce").fillna(0)
    df["是否优秀视频"] = pd.to_numeric(df["是否优秀视频"], errors="coerce").fillna(0).astype(int)

    return df


def run_teacher_exercise_dashboard():
    st.subheader("家庭运动记录与视频反馈（教师端）")
    st.caption("查看学生家庭运动打卡、视频上传情况，并进行教师反馈")

    rows = get_all_exercise_records()
    if not rows:
        st.warning("当前暂无学生家庭运动打卡记录。")
        return

    df = normalize_records(rows)
    if df.empty:
        st.warning("当前暂无可用的家庭运动记录。")
        return

    st.markdown("### 筛选条件")

    class_options = ["全部"] + sorted(
        [x for x in df["班级"].dropna().astype(str).unique().tolist() if str(x).strip() != ""]
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        selected_class = st.selectbox("选择班级", class_options)
    with c2:
        show_video_only = st.checkbox("只看视频打卡", value=False)
    with c3:
        show_unreviewed_only = st.checkbox("只看未反馈记录", value=False)
    with c4:
        show_featured_only = st.checkbox("只看优秀视频", value=False)

    filtered_df = df.copy()

    if selected_class != "全部":
        filtered_df = filtered_df[filtered_df["班级"] == selected_class].copy()

    if show_video_only:
        filtered_df = filtered_df[
            filtered_df["视频路径"].notna() & (filtered_df["视频路径"].astype(str).str.strip() != "")
        ].copy()

    if show_unreviewed_only:
        filtered_df = filtered_df[
            filtered_df["反馈状态"].fillna("未反馈") != "已反馈"
        ].copy()

    if show_featured_only:
        filtered_df = filtered_df[
            filtered_df["是否优秀视频"].fillna(0).astype(int) == 1
        ].copy()

    if filtered_df.empty:
        st.info("当前筛选条件下没有记录。")
        return

    st.markdown("### 1. 本周整体活跃度")

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    df_valid_date = df.dropna(subset=["运动日期"]).copy()
    df_valid_date["运动日期_date"] = df_valid_date["运动日期"].dt.date

    if selected_class != "全部":
        df_valid_date = df_valid_date[df_valid_date["班级"] == selected_class].copy()

    df_week = df_valid_date[
        (df_valid_date["运动日期_date"] >= week_start) &
        (df_valid_date["运动日期_date"] <= week_end)
    ].copy()

    total_records = len(df_week)
    total_students = df_week["学号"].nunique() if not df_week.empty else 0
    avg_duration = round(df_week["运动时长(分钟)"].mean(), 1) if not df_week.empty else 0
    video_count = 0 if df_week.empty else int(
        (
            df_week["视频路径"].notna() &
            (df_week["视频路径"].astype(str).str.strip() != "")
        ).sum()
    )
    featured_count = 0 if df_week.empty else int(
        (df_week["是否优秀视频"].fillna(0).astype(int) == 1).sum()
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("本周打卡总次数", total_records)
    m2.metric("参与学生数", total_students)
    m3.metric("平均运动时长", avg_duration)
    m4.metric("本周视频打卡数", video_count)
    m5.metric("本周优秀视频数", featured_count)

    if not df_week.empty:
        activity_summary = (
            df_week.groupby("班级")["学号"]
            .nunique()
            .reset_index()
            .rename(columns={"学号": "活跃学生数"})
            .sort_values("活跃学生数", ascending=False)
        )
        st.dataframe(activity_summary, use_container_width=True)
    else:
        st.info("本周暂无家庭运动记录。")

    st.markdown("### 2. 本周未打卡学生名单")

    all_students = df[["学号", "姓名", "班级"]].drop_duplicates().copy()
    if selected_class != "全部":
        all_students = all_students[all_students["班级"] == selected_class].copy()

    if all_students.empty:
        st.info("暂无学生基础数据。")
    else:
        active_students = set(df_week["学号"].unique()) if not df_week.empty else set()
        inactive_students = all_students[~all_students["学号"].isin(active_students)].copy()

        if inactive_students.empty:
            st.success("本周所有已登记学生均有家庭运动记录。")
        else:
            st.warning(f"本周未打卡学生数：{len(inactive_students)}")
            st.dataframe(inactive_students, use_container_width=True)

    st.markdown("### 3. 家庭运动排行榜（本周打卡次数）")

    if df_week.empty:
        st.info("本周暂无可统计的排行榜数据。")
    else:
        freq_summary = (
            df_week.groupby(["学号", "姓名", "班级"])["运动日期"]
            .count()
            .reset_index(name="本周运动次数")
            .sort_values("本周运动次数", ascending=False)
        )
        st.dataframe(freq_summary, use_container_width=True)

    st.markdown("### 4. 家庭运动类型统计")

    if df_week.empty:
        st.info("本周暂无运动类型统计数据。")
    else:
        type_summary = df_week["运动类型"].value_counts().reset_index()
        type_summary.columns = ["运动类型", "次数"]

        fig_type = px.bar(
            type_summary,
            x="运动类型",
            y="次数",
            title="本周家庭运动类型分布"
        )
        fig_type.update_layout(height=360)
        st.plotly_chart(fig_type, use_container_width=True)

    st.markdown("### 5. 视频打卡查看与教师反馈")

    video_df = filtered_df[
        filtered_df["视频路径"].notna() &
        (filtered_df["视频路径"].astype(str).str.strip() != "")
    ].copy()

    if video_df.empty:
        st.info("当前筛选条件下暂无视频打卡记录。")
    else:
        st.caption("可以查看学生上传的视频，并填写教师反馈。")

        for _, row in video_df.sort_values(["运动日期", "提交时间"], ascending=[False, False]).iterrows():
            record_id = row["记录ID"]
            title = f"{row['学号']}｜{row['姓名']}｜{row['运动日期'].strftime('%Y-%m-%d') if pd.notna(row['运动日期']) else '-'}｜{row['运动类型']}"

            with st.expander(title, expanded=False):
                a1, a2 = st.columns(2)
                with a1:
                    st.write(f"**班级：** {row['班级']}")
                    st.write(f"**运动时长：** {int(row['运动时长(分钟)'])} 分钟")
                    st.write(f"**运动强度：** {row['运动强度']}")
                    st.write(f"**上传类型：** {row['上传类型']}")
                with a2:
                    st.write(f"**备注：** {row['备注'] if pd.notna(row['备注']) and str(row['备注']).strip() else '无'}")
                    st.write(f"**反馈状态：** {row['反馈状态'] if pd.notna(row['反馈状态']) else '未反馈'}")
                    st.write(f"**已有评价：** {row['教师评价'] if pd.notna(row['教师评价']) else '未评价'}")
                    st.write(f"**优秀视频：** {'是' if int(row['是否优秀视频']) == 1 else '否'}")

                video_path = row["视频路径"]
                if pd.notna(video_path) and str(video_path).strip():
                    try:
                        if os.path.exists(video_path):
                            with open(video_path, "rb") as f:
                                st.video(f.read())
                        else:
                            st.warning("视频路径存在，但本地文件未找到。")
                    except Exception as e:
                        st.warning(f"视频加载失败：{e}")

                default_feedback = row["教师反馈"] if pd.notna(row["教师反馈"]) else ""
                feedback = st.text_area(
                    f"教师反馈_{record_id}",
                    value=default_feedback,
                    placeholder="请输入对学生本次运动打卡的反馈建议或鼓励语。"
                )

                rating_options = ["未评价", "优秀", "良好", "完成", "待补充"]
                current_rating = row["教师评价"] if pd.notna(row["教师评价"]) else "未评价"
                rating_index = rating_options.index(current_rating) if current_rating in rating_options else 0

                rating = st.selectbox(
                    f"评价等级_{record_id}",
                    rating_options,
                    index=rating_index
                )

                st.markdown("### ⭐ 优秀视频设置")
                featured_default = int(row["是否优秀视频"]) == 1 if pd.notna(row["是否优秀视频"]) else False
                is_featured = st.checkbox(
                    "设为优秀视频",
                    value=featured_default,
                    key=f"featured_{record_id}"
                )

                if st.button(f"保存反馈_{record_id}"):
                    try:
                        update_teacher_feedback(
                            record_id=record_id,
                            feedback=feedback,
                            rating=rating,
                            is_featured=1 if is_featured else 0
                        )
                        st.success("教师反馈已保存。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"保存反馈失败：{e}")

                if st.button(f"删除该视频打卡记录_{record_id}"):
                    try:
                        delete_exercise_record_by_id(record_id)
                        st.success("该记录已删除。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"删除失败：{e}")

    st.markdown("### 6. 家庭运动详细记录")

    show_df = filtered_df.copy()

    if "运动日期" in show_df.columns:
        show_df["运动日期"] = show_df["运动日期"].dt.strftime("%Y-%m-%d")
    if "提交时间" in show_df.columns:
        show_df["提交时间"] = show_df["提交时间"].dt.strftime("%Y-%m-%d %H:%M:%S")

    show_df["是否视频打卡"] = show_df["视频路径"].apply(
        lambda x: "是" if pd.notna(x) and str(x).strip() != "" else "否"
    )
    show_df["优秀视频"] = show_df["是否优秀视频"].apply(
        lambda x: "是" if pd.notna(x) and int(x) == 1 else "否"
    )

    keep_cols = [
        "学号", "姓名", "班级", "运动日期", "运动类型",
        "运动时长(分钟)", "运动强度", "备注", "是否视频打卡",
        "优秀视频", "反馈状态", "教师评价", "提交时间"
    ]
    keep_cols = [c for c in keep_cols if c in show_df.columns]

    st.dataframe(show_df[keep_cols], use_container_width=True)

    csv_data = show_df[keep_cols].to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "下载家庭运动记录 CSV",
        csv_data,
        "家庭运动记录_教师端.csv",
        "text/csv"
    )
