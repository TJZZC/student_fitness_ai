import os
import sqlite3
from datetime import datetime, date, timedelta

# =========================
# 路径配置
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads", "exercise_videos")
DB_PATH = os.path.join(DATA_DIR, "student_system.db")


# =========================
# 基础工具
# =========================
def ensure_dirs():
    """确保数据目录和上传目录存在"""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_connection():
    """获取数据库连接，并设置 row_factory 方便按字段名取值"""
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# =========================
# 数据库初始化
# =========================
def init_db():
    """初始化数据库与表"""
    ensure_dirs()
    conn = get_connection()
    cursor = conn.cursor()

    # 学生注册表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT NOT NULL,
            gender TEXT,
            age INTEGER,
            class_name TEXT,
            phone TEXT,
            created_at TEXT
        )
    """)

    # 家庭运动打卡表（含视频、教师反馈、优秀视频标记）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exercise_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            exercise_date TEXT NOT NULL,
            exercise_type TEXT NOT NULL,
            duration_minutes INTEGER NOT NULL,
            intensity TEXT,
            remark TEXT,
            created_at TEXT,

            video_path TEXT,
            video_filename TEXT,
            upload_type TEXT DEFAULT 'text',

            teacher_feedback TEXT,
            teacher_rating TEXT,
            teacher_feedback_at TEXT,
            review_status TEXT DEFAULT '未反馈',
            is_featured INTEGER DEFAULT 0
        )
    """)

    # 体测成绩表（原始值 + 标准评分 + 总分 + 等级）
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fitness_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            test_date TEXT NOT NULL,

            grade TEXT,
            gender TEXT,

            height_cm REAL,
            weight_kg REAL,
            bmi REAL,

            lung_capacity REAL,
            sprint_50m REAL,
            sit_and_reach REAL,
            standing_long_jump REAL,
            endurance_run REAL,
            strength REAL,

            bmi_score REAL,
            lung_capacity_score REAL,
            sprint_50m_score REAL,
            sit_and_reach_score REAL,
            standing_long_jump_score REAL,
            endurance_score REAL,
            strength_score REAL,

            total_score REAL,
            level TEXT,
            weak_items TEXT,

            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    # 兼容旧数据库，自动补列
    ensure_exercise_record_columns()


def ensure_exercise_record_columns():
    """兼容旧库：如果 exercise_records 缺少新字段，则自动补上"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(exercise_records)")
    columns = [row[1] for row in cursor.fetchall()]

    extra_columns = {
        "video_path": "TEXT",
        "video_filename": "TEXT",
        "upload_type": "TEXT DEFAULT 'text'",
        "teacher_feedback": "TEXT",
        "teacher_rating": "TEXT",
        "teacher_feedback_at": "TEXT",
        "review_status": "TEXT DEFAULT '未反馈'",
        "is_featured": "INTEGER DEFAULT 0"
    }

    for col_name, col_type in extra_columns.items():
        if col_name not in columns:
            cursor.execute(f"ALTER TABLE exercise_records ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()


# =========================
# 学生注册 / 登录
# =========================
def register_student(student_id, password, name, gender=None, age=None, class_name=None, phone=None):
    """学生注册"""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO students (
                student_id, password, name, gender, age, class_name, phone, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            student_id,
            password,
            name,
            gender,
            age,
            class_name,
            phone,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True, "注册成功"
    except sqlite3.IntegrityError:
        return False, "学号已存在，请更换学号"
    except Exception as e:
        return False, f"注册失败：{str(e)}"
    finally:
        conn.close()


def verify_student_login(student_id, password):
    """学生登录校验"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE student_id = ? AND password = ?
    """, (student_id, password))

    row = cursor.fetchone()
    conn.close()

    if row:
        return True, dict(row)
    return False, None


def get_student_info(student_id):
    """获取单个学生信息"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        WHERE student_id = ?
    """, (student_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_all_students():
    """获取全部注册学生"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM students
        ORDER BY created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# =========================
# 视频文件处理
# =========================
def _safe_folder_name(value):
    """
    生成安全的文件夹名，避免出现 Windows 非法字符
    """
    if value is None:
        return "未知"
    value = str(value).strip()
    if not value:
        return "未知"

    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        value = value.replace(ch, "_")

    return value


def save_uploaded_video(student_id, uploaded_file, class_name=None, exercise_date=None):
    """
    保存学生上传的视频文件到本地
    目录结构：
    uploads/exercise_videos/班级/学号/日期/文件

    返回:
    (video_path, original_filename)
    """
    if uploaded_file is None:
        return None, None

    ensure_dirs()

    student_id = str(student_id).zfill(3)
    class_folder = _safe_folder_name(class_name) if class_name else "未分班"
    date_folder = str(exercise_date) if exercise_date else datetime.now().strftime("%Y-%m-%d")

    target_dir = os.path.join(
        UPLOAD_DIR,
        class_folder,
        student_id,
        date_folder
    )
    os.makedirs(target_dir, exist_ok=True)

    original_filename = uploaded_file.name
    ext = original_filename.split(".")[-1].lower() if "." in original_filename else "mp4"

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    safe_filename = f"{student_id}_{timestamp}.{ext}"
    file_path = os.path.join(target_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    return file_path, original_filename


# =========================
# 打卡记录新增
# =========================
def add_exercise_record(
    student_id,
    exercise_date,
    exercise_type,
    duration_minutes,
    intensity="中等",
    remark="",
    video_path=None,
    video_filename=None,
    upload_type="text"
):
    """新增一条运动打卡记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO exercise_records (
            student_id,
            exercise_date,
            exercise_type,
            duration_minutes,
            intensity,
            remark,
            created_at,
            video_path,
            video_filename,
            upload_type,
            teacher_feedback,
            teacher_rating,
            teacher_feedback_at,
            review_status,
            is_featured
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id,
        str(exercise_date),
        exercise_type,
        int(duration_minutes),
        intensity,
        remark,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        video_path,
        video_filename,
        upload_type,
        None,
        None,
        None,
        "未反馈",
        0
    ))

    conn.commit()
    conn.close()


# =========================
# 打卡记录查询
# =========================
def get_student_exercise_records(student_id):
    """获取某个学生的全部打卡记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM exercise_records
        WHERE student_id = ?
        ORDER BY exercise_date DESC, created_at DESC
    """, (student_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_all_exercise_records():
    """获取全部学生运动记录，并关联学生信息"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            er.*,
            s.name,
            s.class_name,
            s.gender,
            s.age,
            s.phone
        FROM exercise_records er
        LEFT JOIN students s
            ON er.student_id = s.student_id
        ORDER BY er.exercise_date DESC, er.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_video_exercise_records():
    """获取全部含视频的打卡记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            er.*,
            s.name,
            s.class_name,
            s.gender,
            s.age,
            s.phone
        FROM exercise_records er
        LEFT JOIN students s
            ON er.student_id = s.student_id
        WHERE er.video_path IS NOT NULL
          AND TRIM(er.video_path) != ''
        ORDER BY er.exercise_date DESC, er.created_at DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_exercise_record_by_id(record_id):
    """按记录ID获取单条打卡记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            er.*,
            s.name,
            s.class_name,
            s.gender,
            s.age,
            s.phone
        FROM exercise_records er
        LEFT JOIN students s
            ON er.student_id = s.student_id
        WHERE er.id = ?
    """, (record_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_records_by_class_name(class_name):
    """按班级获取运动记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            er.*,
            s.name,
            s.class_name
        FROM exercise_records er
        LEFT JOIN students s
            ON er.student_id = s.student_id
        WHERE s.class_name = ?
        ORDER BY er.exercise_date DESC, er.created_at DESC
    """, (class_name,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


# =========================
# 体测成绩管理
# =========================
def add_fitness_test_record(
    student_id,
    test_date,
    grade,
    gender,
    height_cm,
    weight_kg,
    bmi,
    lung_capacity,
    sprint_50m,
    sit_and_reach,
    standing_long_jump,
    endurance_run,
    strength,
    score_result
):
    """
    新增一条体测记录，并保存标准评分结果
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO fitness_tests (
            student_id,
            test_date,
            grade,
            gender,
            height_cm,
            weight_kg,
            bmi,
            lung_capacity,
            sprint_50m,
            sit_and_reach,
            standing_long_jump,
            endurance_run,
            strength,
            bmi_score,
            lung_capacity_score,
            sprint_50m_score,
            sit_and_reach_score,
            standing_long_jump_score,
            endurance_score,
            strength_score,
            total_score,
            level,
            weak_items,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        student_id,
        str(test_date),
        grade,
        gender,
        float(height_cm) if height_cm is not None else None,
        float(weight_kg) if weight_kg is not None else None,
        float(bmi) if bmi is not None else None,
        float(lung_capacity) if lung_capacity is not None else None,
        float(sprint_50m) if sprint_50m is not None else None,
        float(sit_and_reach) if sit_and_reach is not None else None,
        float(standing_long_jump) if standing_long_jump is not None else None,
        float(endurance_run) if endurance_run is not None else None,
        float(strength) if strength is not None else None,
        float(score_result.bmi_score),
        float(score_result.lung_capacity_score),
        float(score_result.sprint_50m_score),
        float(score_result.sit_and_reach_score),
        float(score_result.standing_long_jump_score),
        float(score_result.endurance_score),
        float(score_result.strength_score),
        float(score_result.total_score),
        score_result.level,
        ",".join(score_result.weak_items),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_student_fitness_tests(student_id):
    """获取某个学生的全部体测记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM fitness_tests
        WHERE student_id = ?
        ORDER BY test_date DESC, created_at DESC, id DESC
    """, (student_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_latest_fitness_test(student_id):
    """获取某个学生最新一次体测记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM fitness_tests
        WHERE student_id = ?
        ORDER BY test_date DESC, created_at DESC, id DESC
        LIMIT 1
    """, (student_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def get_all_fitness_tests():
    """获取全部体测记录，并关联学生信息"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            ft.*,
            s.name,
            s.class_name,
            s.age,
            s.phone
        FROM fitness_tests ft
        LEFT JOIN students s
            ON ft.student_id = s.student_id
        ORDER BY ft.test_date DESC, ft.created_at DESC, ft.id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def delete_fitness_test_by_id(record_id):
    """删除一条体测记录"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM fitness_tests
        WHERE id = ?
    """, (record_id,))

    conn.commit()
    conn.close()

    return True


# =========================
# 教师反馈
# =========================
def update_teacher_feedback(record_id, feedback, rating, is_featured=0):
    """教师对某条打卡记录进行反馈，并可标记为优秀视频"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE exercise_records
        SET teacher_feedback = ?,
            teacher_rating = ?,
            teacher_feedback_at = ?,
            review_status = ?,
            is_featured = ?
        WHERE id = ?
    """, (
        feedback,
        rating,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "已反馈",
        int(is_featured),
        record_id
    ))

    conn.commit()
    conn.close()


# =========================
# 删除记录
# =========================
def delete_exercise_record_by_id(record_id):
    """
    教师端删除任意一条运动记录。
    如果有视频文件，会同时尝试删除本地文件。
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT video_path
        FROM exercise_records
        WHERE id = ?
    """, (record_id,))
    row = cursor.fetchone()

    video_path = row["video_path"] if row and "video_path" in row.keys() else None

    cursor.execute("""
        DELETE FROM exercise_records
        WHERE id = ?
    """, (record_id,))

    conn.commit()
    conn.close()

    if video_path and os.path.exists(video_path):
        try:
            os.remove(video_path)
        except Exception:
            pass

    return True


def delete_student_own_exercise_record(record_id, student_id):
    """
    学生端删除自己的运动记录。
    只能删除 student_id 对应的记录。
    如果有视频文件，会同时尝试删除本地文件。
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT video_path
        FROM exercise_records
        WHERE id = ? AND student_id = ?
    """, (record_id, student_id))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return False, "未找到该记录，或无权限删除"

    video_path = row["video_path"] if "video_path" in row.keys() else None

    cursor.execute("""
        DELETE FROM exercise_records
        WHERE id = ? AND student_id = ?
    """, (record_id, student_id))

    conn.commit()
    conn.close()

    if video_path and os.path.exists(video_path):
        try:
            os.remove(video_path)
        except Exception:
            pass

    return True, "删除成功"


# =========================
# 统计辅助函数
# =========================
def has_checked_in_today(student_id):
    """判断学生今天是否已打卡"""
    today_str = date.today().strftime("%Y-%m-%d")
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) as cnt
        FROM exercise_records
        WHERE student_id = ?
          AND exercise_date = ?
    """, (student_id, today_str))

    row = cursor.fetchone()
    conn.close()

    return row["cnt"] > 0


def get_this_week_records(student_id):
    """获取学生本周打卡记录"""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM exercise_records
        WHERE student_id = ?
          AND exercise_date >= ?
          AND exercise_date <= ?
        ORDER BY exercise_date DESC, created_at DESC
    """, (
        student_id,
        monday.strftime("%Y-%m-%d"),
        sunday.strftime("%Y-%m-%d")
    ))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def get_total_exercise_minutes(student_id):
    """获取学生累计运动分钟数"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(duration_minutes), 0) AS total_minutes
        FROM exercise_records
        WHERE student_id = ?
    """, (student_id,))

    row = cursor.fetchone()
    conn.close()

    return row["total_minutes"] if row else 0


def get_video_checkin_count(student_id):
    """获取学生视频打卡次数"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS cnt
        FROM exercise_records
        WHERE student_id = ?
          AND video_path IS NOT NULL
          AND TRIM(video_path) != ''
    """, (student_id,))

    row = cursor.fetchone()
    conn.close()

    return row["cnt"] if row else 0


# =========================
# 旧版本兼容函数
# =========================
def get_exercise_records_by_student(student_id):
    return get_student_exercise_records(student_id)


def get_all_student_exercise_records(student_id):
    return get_student_exercise_records(student_id)


def get_student_by_id(student_id):
    return get_student_info(student_id)


def get_exercise_records(student_id):
    return get_student_exercise_records(student_id)


# =========================
# 调试 / 单独运行初始化
# =========================
if __name__ == "__main__":
    init_db()
    print("数据库初始化完成：", DB_PATH)
