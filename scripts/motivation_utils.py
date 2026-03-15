import pandas as pd
from datetime import date, timedelta


# =========================
# 内部工具：标准化运动记录
# =========================
def _normalize_exercise_df(exercise_df):
    """
    统一处理运动记录数据，兼容：
    - DataFrame
    - list[dict]
    - 单纯 list

    输出统一字段：
    - 运动日期
    - 运动类型
    - 运动时长(分钟)
    - 视频路径
    - 教师评价
    """
    if exercise_df is None:
        return pd.DataFrame()

    # 1. 先转 DataFrame
    if isinstance(exercise_df, pd.DataFrame):
        df = exercise_df.copy()
    elif isinstance(exercise_df, list):
        if len(exercise_df) == 0:
            return pd.DataFrame()
        df = pd.DataFrame(exercise_df).copy()
    else:
        try:
            df = pd.DataFrame(exercise_df).copy()
        except Exception:
            return pd.DataFrame()

    if df.empty:
        return pd.DataFrame()

    # 2. 兼容英文/数据库字段名 -> 中文分析字段名
    rename_map = {
        "exercise_date": "运动日期",
        "exercise_type": "运动类型",
        "duration_minutes": "运动时长(分钟)",
        "video_path": "视频路径",
        "teacher_rating": "教师评价"
    }
    df = df.rename(columns=rename_map)

    # 3. 日期字段标准化
    if "运动日期" in df.columns:
        df["运动日期"] = pd.to_datetime(df["运动日期"], errors="coerce").dt.date

    # 4. 时长字段标准化
    if "运动时长(分钟)" in df.columns:
        df["运动时长(分钟)"] = pd.to_numeric(
            df["运动时长(分钟)"], errors="coerce"
        ).fillna(0)

    # 5. 补齐可能会用到的列，避免后续 KeyError
    for col in ["运动日期", "运动类型", "运动时长(分钟)", "视频路径", "教师评价"]:
        if col not in df.columns:
            df[col] = None

    return df



# =========================
# 计算连续打卡天数
# =========================
def calc_consecutive_days(exercise_df):
    """
    连续打卡定义：
    - 以最近一次打卡日期为起点
    - 往前连续相差1天则累计
    """
    df = _normalize_exercise_df(exercise_df)

    if df.empty or "运动日期" not in df.columns:
        return 0

    df = df.dropna(subset=["运动日期"]).copy()
    if df.empty:
        return 0

    unique_dates = sorted(set(df["运动日期"].tolist()), reverse=True)
    if not unique_dates:
        return 0

    consecutive = 1
    for i in range(len(unique_dates) - 1):
        if (unique_dates[i] - unique_dates[i + 1]).days == 1:
            consecutive += 1
        else:
            break

    return consecutive


# =========================
# 获取本周记录
# =========================
def get_week_records(exercise_df):
    df = _normalize_exercise_df(exercise_df)

    if df.empty or "运动日期" not in df.columns:
        return pd.DataFrame(columns=df.columns if not df.empty else [])

    df = df.dropna(subset=["运动日期"]).copy()
    if df.empty:
        return df

    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    return df[
        (df["运动日期"] >= week_start) &
        (df["运动日期"] <= week_end)
    ].copy()


# =========================
# 获取最近7天记录
# =========================
def get_recent_7day_records(exercise_df):
    df = _normalize_exercise_df(exercise_df)

    if df.empty or "运动日期" not in df.columns:
        return pd.DataFrame(columns=df.columns if not df.empty else [])

    df = df.dropna(subset=["运动日期"]).copy()
    if df.empty:
        return df

    today = date.today()
    start_day = today - timedelta(days=6)

    return df[
        (df["运动日期"] >= start_day) &
        (df["运动日期"] <= today)
    ].copy()


# =========================
# 统计学生运动数据
# =========================
def get_student_motivation_stats(exercise_df):
    df = _normalize_exercise_df(exercise_df)

    if df.empty:
        return {
            "week_count": 0,
            "consecutive_days": 0,
            "total_duration": 0,
            "week_duration": 0,
            "exercise_type_count": 0,
            "video_count": 0,
            "excellent_video_count": 0
        }

    week_df = get_week_records(df)
    consecutive_days = calc_consecutive_days(df)

    total_duration = 0
    if "运动时长(分钟)" in df.columns:
        total_duration = int(df["运动时长(分钟)"].fillna(0).sum())

    week_duration = 0
    if not week_df.empty and "运动时长(分钟)" in week_df.columns:
        week_duration = int(week_df["运动时长(分钟)"].fillna(0).sum())

    exercise_type_count = 0
    if "运动类型" in df.columns:
        exercise_type_count = df["运动类型"].dropna().astype(str).str.strip()
        exercise_type_count = exercise_type_count[exercise_type_count != ""].nunique()

    # 视频打卡统计（兼容新系统）
    video_count = 0
    if "视频路径" in df.columns:
        video_count = int(
            (
                df["视频路径"].notna() &
                (df["视频路径"].astype(str).str.strip() != "")
            ).sum()
        )

    excellent_video_count = 0
    if "教师评价" in df.columns:
        excellent_video_count = int((df["教师评价"] == "优秀").sum())

    return {
        "week_count": len(week_df),
        "consecutive_days": consecutive_days,
        "total_duration": total_duration,
        "week_duration": week_duration,
        "exercise_type_count": exercise_type_count,
        "video_count": video_count,
        "excellent_video_count": excellent_video_count
    }


# =========================
# 奖牌判定
# =========================
def get_student_medals(stats):
    medals = []

    if stats.get("consecutive_days", 0) >= 3:
        medals.append("坚持起步奖")

    if stats.get("week_count", 0) >= 3:
        medals.append("本周达标奖")

    if stats.get("week_count", 0) >= 5:
        medals.append("运动之星奖")

    if stats.get("total_duration", 0) >= 300:
        medals.append("活力成长奖")

    if stats.get("exercise_type_count", 0) >= 3:
        medals.append("全面发展奖")

    if stats.get("consecutive_days", 0) >= 7:
        medals.append("自律达人奖")

    return medals


# =========================
# 下一个奖牌目标提示
# =========================
def get_next_medal_tip(stats):
    tips = []

    if stats.get("consecutive_days", 0) < 3:
        tips.append(f"再连续打卡 {3 - stats['consecutive_days']} 天，可获得“坚持起步奖”")

    if stats.get("week_count", 0) < 3:
        tips.append(f"本周再完成 {3 - stats['week_count']} 次运动，可获得“本周达标奖”")

    if stats.get("week_count", 0) < 5:
        tips.append(f"本周再完成 {5 - stats['week_count']} 次运动，可获得“运动之星奖”")

    if stats.get("total_duration", 0) < 300:
        tips.append(f"累计再运动 {300 - stats['total_duration']} 分钟，可获得“活力成长奖”")

    if stats.get("exercise_type_count", 0) < 3:
        tips.append(f"再完成 {3 - stats['exercise_type_count']} 种不同运动，可获得“全面发展奖”")

    if stats.get("consecutive_days", 0) < 7:
        tips.append(f"再连续打卡 {7 - stats['consecutive_days']} 天，可获得“自律达人奖”")

    return tips[:2]


# =========================
# 兼容命名：给学生端用的提示函数
# =========================
def get_next_goal_tip(exercise_df_or_stats):
    """
    兼容 student_exercise_dashboard.py 里的调用习惯：
    既支持传 stats，也支持直接传 exercise_df
    """
    if isinstance(exercise_df_or_stats, dict):
        stats = exercise_df_or_stats
    else:
        stats = get_student_motivation_stats(exercise_df_or_stats)

    tips = get_next_medal_tip(stats)
    if tips:
        return "；".join(tips)

    return "继续保持，你已经达成了当前阶段的主要运动目标。"


# =========================
# 计算排行榜积分
# =========================
def calc_rank_score(stats):
    """
    当前积分规则：
    - 本周打卡次数：每次 10 分
    - 本周运动时长：每 10 分钟 1 分
    - 连续打卡天数：每天 5 分
    - 视频打卡：每次 2 分
    - 教师评价为优秀：每次 3 分
    """
    base_score = (
        stats.get("week_count", 0) * 10 +
        stats.get("week_duration", 0) / 10 +
        stats.get("consecutive_days", 0) * 5
    )

    video_bonus = stats.get("video_count", 0) * 2
    excellent_bonus = stats.get("excellent_video_count", 0) * 3

    return round(base_score + video_bonus + excellent_bonus, 1)


# =========================
# 兼容旧命名
# =========================
def calculate_consecutive_checkin_days(exercise_df):
    return calc_consecutive_days(exercise_df)


def calculate_student_points(exercise_df_or_stats):
    if isinstance(exercise_df_or_stats, dict):
        stats = exercise_df_or_stats
    else:
        stats = get_student_motivation_stats(exercise_df_or_stats)
    return calc_rank_score(stats)
