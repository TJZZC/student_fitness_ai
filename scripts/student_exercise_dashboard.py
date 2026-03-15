import os
import streamlit as st
import pandas as pd
from datetime import date, timedelta

from scripts.db_utils import (
    init_db,
    get_student_info,
    has_checked_in_today,
    get_this_week_records,
    get_total_exercise_minutes,
    get_student_exercise_records,
    add_exercise_record,
    save_uploaded_video,
    get_video_checkin_count,
    delete_student_own_exercise_record
)

from scripts.motivation_utils import (
    get_student_motivation_stats,
    calculate_consecutive_checkin_days,
    get_student_medals,
    get_next_goal_tip,
    calculate_student_points
)


def _render_metrics(student_id, records):
    today_checked = has_checked_in_today(student_id)
    this_week_records = get_this_week_records(student_id)
    total_minutes = get_total_exercise_minutes(student_id)
    video_count = get_video_checkin_count(student_id)
    streak_days = calculate_consecutive_checkin_days(records)
    total_points = calculate_student_points(records)

    c1, c2 = st.columns(2)
    with c1:
        st.metric("今日打卡", "已完成" if today_checked else "未打卡")
        st.metric("连续打卡", f"{streak_days} 天")
        st.metric("视频打卡次数", f"{video_count} 次")

    with c2:
        st.metric("本周打卡次数", f"{len(this_week_records)} 次")
        st.metric("累计运动时长", f"{total_minutes} 分钟")
        st.metric("综合积分", f"{total_points} 分")


def _render_medals_and_feedback(records):
    st.subheader("🏅 我的成长激励")

    stats = get_student_motivation_stats(records)
    medals = get_student_medals(stats)
    goal_tip = get_next_goal_tip(stats)

    if medals:
        medal_text = " / ".join(medals)
        st.success(f"已获得奖牌：{medal_text}")
    else:
        st.info("你还没有获得奖牌，继续努力，今天就动起来！")

    st.caption(f"成长目标提示：{goal_tip}")


def _render_checkin_form(student_id):
    st.subheader("🎥 家庭运动打卡")

    student_info = get_student_info(str(student_id).zfill(3))
    class_name = student_info.get("class_name", "未分班") if student_info else "未分班"

    with st.form("exercise_checkin_form", clear_on_submit=True):
        exercise_date = st.date_input("运动日期", value=date.today())
        exercise_type = st.selectbox(
            "运动类型",
            ["跑步", "跳绳", "篮球", "足球", "羽毛球", "乒乓球", "仰卧起坐", "引体向上", "健身操", "其他"]
        )
        duration_minutes = st.number_input(
            "运动时长（分钟）",
            min_value=1,
            max_value=300,
            value=30,
            step=1
        )
        intensity = st.selectbox("运动强度", ["低", "中等", "高"], index=1)
        remark = st.text_area("备注（可选）", placeholder="例如：今天和家长一起跑步，状态不错。")

        uploaded_video = st.file_uploader(
            "上传运动视频（可选）",
            type=["mp4", "mov", "avi"],
            help="建议上传 30 秒到 2 分钟的视频，用于教师查看和反馈。"
        )

        submit = st.form_submit_button("提交打卡")

        if submit:
            if not exercise_type:
                st.error("请选择运动类型")
                st.stop()

            video_path, video_filename = None, None
            upload_type = "text"

            if uploaded_video is not None:
                max_size_mb = 50
                file_size_mb = uploaded_video.size / (1024 * 1024)

                if file_size_mb > max_size_mb:
                    st.error(f"视频文件不能超过 {max_size_mb}MB")
                    st.stop()

                try:
                    video_path, video_filename = save_uploaded_video(
                        student_id=student_id,
                        uploaded_file=uploaded_video,
                        class_name=class_name,
                        exercise_date=exercise_date
                    )
                    upload_type = "video"
                except Exception as e:
                    st.error(f"视频保存失败：{str(e)}")
                    st.stop()

            try:
                add_exercise_record(
                    student_id=student_id,
                    exercise_date=str(exercise_date),
                    exercise_type=exercise_type,
                    duration_minutes=int(duration_minutes),
                    intensity=intensity,
                    remark=remark,
                    video_path=video_path,
                    video_filename=video_filename,
                    upload_type=upload_type
                )
                st.success("打卡提交成功！")
                if upload_type == "video":
                    st.info("本次为视频打卡，教师端可以查看并给你反馈。")
                st.rerun()
            except Exception as e:
                st.error(f"提交失败：{str(e)}")


def _render_recent_week_calendar(records):
    st.subheader("📅 最近7天打卡情况")

    today = date.today()
    date_map = {}

    for r in records:
        d = str(r.get("exercise_date", "")).strip()
        if d:
            date_map[d] = date_map.get(d, 0) + 1

    rows = []
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        d_str = d.strftime("%Y-%m-%d")
        checked = "✅" if d_str in date_map else "⬜"

        rows.append({
            "日期": d_str,
            "星期": weekday_map[d.weekday()],
            "状态": checked,
            "次数": date_map.get(d_str, 0)
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_history(student_id, records):
    st.subheader("📚 我的历史打卡记录")

    if not records:
        st.info("还没有打卡记录，快去完成第一次运动打卡吧。")
        return

    for idx, record in enumerate(records):
        record_id = record.get("id")
        exercise_date = record.get("exercise_date", "")
        exercise_type = record.get("exercise_type", "")
        duration_minutes = record.get("duration_minutes", 0)
        intensity = record.get("intensity", "")
        remark = record.get("remark", "") or "无"
        video_path = record.get("video_path")
        video_filename = record.get("video_filename")
        review_status = record.get("review_status", "未反馈")
        teacher_feedback = record.get("teacher_feedback")
        teacher_rating = record.get("teacher_rating")
        teacher_feedback_at = record.get("teacher_feedback_at")
        is_featured = record.get("is_featured", 0)

        title = f"{exercise_date}｜{exercise_type}｜{duration_minutes}分钟"

        with st.expander(title, expanded=(idx == 0)):
            st.write(f"**运动强度：** {intensity}")
            st.write(f"**备注：** {remark}")

            if video_path:
                st.write("**视频打卡：** 已上传")
                if video_filename:
                    st.caption(f"原文件名：{video_filename}")

                try:
                    if os.path.exists(video_path):
                        with open(video_path, "rb") as f:
                            st.video(f.read())
                    else:
                        st.warning("视频文件路径存在，但本地文件未找到。")
                except Exception as e:
                    st.warning(f"视频加载失败：{str(e)}")
            else:
                st.write("**视频打卡：** 未上传")

            st.write(f"**教师反馈状态：** {review_status}")

            if str(is_featured) == "1":
                st.success("🌟 本次视频打卡已被教师评为优秀案例")

            if teacher_rating:
                st.write(f"**教师评价：** {teacher_rating}")

            if teacher_feedback:
                st.info(f"教师反馈：{teacher_feedback}")

            if teacher_feedback_at:
                st.caption(f"反馈时间：{teacher_feedback_at}")

            st.markdown("---")
            st.caption("如误提交，可删除本条记录后重新打卡。")

            if record_id is not None:
                if st.button(f"删除这条打卡记录_{record_id}"):
                    ok, msg = delete_student_own_exercise_record(
                        record_id=record_id,
                        student_id=student_id
                    )
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)


def run_student_exercise_dashboard(student_id):
    init_db()

    st.title("家庭运动打卡与成长反馈")

    if not student_id:
        st.error("未获取到当前登录学生学号，请重新登录。")
        return

    student_id = str(student_id).zfill(3)

    student_info = get_student_info(student_id)
    if not student_info:
        st.error("未找到当前学生信息，请确认账号是否已注册。")
        return

    st.caption(
        f"当前学生：{student_info.get('name', '-')}"
        f"｜学号：{student_info.get('student_id', '-')}"
        f"｜班级：{student_info.get('class_name', '-')}"
    )

    records = get_student_exercise_records(student_id)

    _render_metrics(student_id, records)
    st.divider()

    _render_medals_and_feedback(records)
    st.divider()

    _render_checkin_form(student_id)
    st.divider()

    _render_recent_week_calendar(records)
    st.divider()

    _render_history(student_id, records)
