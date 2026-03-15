import streamlit as st
from scripts.auth import init_session, login_page, logout_button
from scripts.db_utils import init_db

st.set_page_config(
    page_title="中学生体质监测与智能分析系统",
    page_icon="🏃",
    layout="wide"
)

st.markdown("""
<link rel="manifest" href="/static/manifest.json">
<script>
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/service-worker.js')
    .then(function(reg) { console.log('Service Worker Registered!', reg); });
}
</script>
""", unsafe_allow_html=True)


# 初始化会话与数据库
init_session()
init_db()

# ===============================
# 全局样式
# ===============================
st.markdown("""
<style>
.block-container {
    padding-top: 1rem;
    padding-bottom: 1rem;
}

[data-testid="stMetricValue"] {
    font-size: 28px;
}

[data-testid="stMetricLabel"] {
    font-size: 16px;
}

.main-title-wrap {
    margin-top: 28px;
    margin-bottom: 6px;
    overflow: visible;
}

.main-title {
    font-size: 28px;
    font-weight: 700;
    color: #1f4e79;
    line-height: 1.7;
    padding-top: 10px;
    padding-bottom: 10px;
    overflow: visible;
    display: block;
}

.sub-title {
    font-size: 16px;
    color: #666666;
    margin-bottom: 1.2rem;
}

.role-box {
    padding: 12px 16px;
    border-radius: 12px;
    background-color: #f4f8fb;
    border: 1px solid #d9e6f2;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)


def render_system_header():
    st.markdown(
        """
        <div class="main-title-wrap">
            <div class="main-title">中学生体质监测与智能分析系统</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="sub-title">
            面向学生体质健康促进、家庭运动打卡、AI预测预警与教师干预管理的家校协同平台
        </div>
        """,
        unsafe_allow_html=True
    )


def render_sidebar_user_info():
    st.sidebar.markdown("## 系统导航")
    st.sidebar.markdown(
        f"""
<div class="role-box">
<b>当前用户：</b> {st.session_state.username}<br>
<b>身份：</b> {st.session_state.role}
</div>
""",
        unsafe_allow_html=True
    )


def run_teacher_pages():
    page = st.sidebar.radio(
        "选择功能",
        [
            "首页",
            "班级分析",
            "数据管理",
            "学生信息管理",
            "体测录入与评分",
            "体测记录管理",
            "体测管理",
            "家庭运动记录",
            "班级预测导出",
            "重点干预名单",
            "运动排行榜"
        ]
    )

    if page == "首页":
        try:
            from scripts.home_dashboard import run_home_dashboard
            run_home_dashboard()
        except Exception as e:
            st.error(f"首页加载失败：{e}")

    elif page == "班级分析":
        try:
            from scripts.visual_dashboard import run_dashboard
            run_dashboard()
        except Exception as e:
            st.error(f"班级分析页面加载失败：{e}")

    elif page == "数据管理":
        try:
            from scripts.data_management_dashboard import run_data_dashboard
            run_data_dashboard()
        except Exception as e:
            st.error(f"数据管理页面加载失败：{e}")

    elif page == "学生信息管理":
        try:
            from scripts.student_registry_dashboard import run_student_registry_dashboard
            run_student_registry_dashboard()
        except Exception as e:
            st.error(f"学生信息管理页面加载失败：{e}")

    elif page == "体测录入与评分":
        try:
            from scripts.fitness_test_dashboard import run_fitness_test_dashboard
            run_fitness_test_dashboard()
        except Exception as e:
            st.error(f"体测录入与评分页面加载失败：{e}")
            
    elif page == "体测记录管理":
        try:
            from scripts.fitness_records_dashboard import run_fitness_records_dashboard
            run_fitness_records_dashboard()
        except Exception as e:
            st.error(f"体测记录管理页面加载失败：{e}")

    elif page == "体测管理":
        try:
            from scripts.fitness_dashboard import run_fitness_dashboard
            run_fitness_dashboard()
        except Exception as e:
            st.error(f"体测管理页面加载失败：{e}")

    elif page == "家庭运动记录":
        try:
            from scripts.teacher_exercise_dashboard import run_teacher_exercise_dashboard
            run_teacher_exercise_dashboard()
        except Exception as e:
            st.error(f"家庭运动记录页面加载失败：{e}")

    elif page == "班级预测导出":
        try:
            from scripts.teacher_prediction_export import run_teacher_prediction_export
            run_teacher_prediction_export()
        except Exception as e:
            st.error(f"班级预测导出页面加载失败：{e}")

    elif page == "重点干预名单":
        try:
            from scripts.intervention_dashboard import run_intervention_dashboard
            run_intervention_dashboard()
        except Exception as e:
            st.error(f"重点干预名单页面加载失败：{e}")

    elif page == "运动排行榜":
        try:
            from scripts.ranking_dashboard import run_ranking_dashboard
            run_ranking_dashboard()
        except Exception as e:
            st.error(f"运动排行榜页面加载失败：{e}")


def run_student_pages():
    page = st.sidebar.radio(
        "选择功能",
        [
            "我的体测档案",
            "体测档案",
            "家庭运动打卡与成长反馈"
        ]
    )

    if page == "我的体测档案":
        try:
            from scripts.student_dashboard import run_student_dashboard
            run_student_dashboard(st.session_state.username)
        except Exception as e:
            st.error(f"学生档案页面加载失败：{e}")
            
    elif page == "体测档案":
        try:
            from scripts.student_fitness_dashboard import run_student_fitness_dashboard
            run_student_fitness_dashboard(st.session_state.username)
        except Exception as e:
            st.error(f"学生档案页面加载失败：{e}")

    elif page == "家庭运动打卡与成长反馈":
        try:
            from scripts.student_exercise_dashboard import run_student_exercise_dashboard
            run_student_exercise_dashboard(st.session_state.username)
        except Exception as e:
            st.error(f"家庭运动打卡页面加载失败：{e}")


# ===============================
# 未登录：显示登录页
# ===============================
if not st.session_state.logged_in:
    login_page()

# ===============================
# 已登录：显示系统页面
# ===============================
else:
    render_system_header()
    render_sidebar_user_info()
    logout_button()

    if st.session_state.role == "教师":
        run_teacher_pages()

    elif st.session_state.role == "学生":
        run_student_pages()

    else:
        st.warning("当前用户角色无效，请重新登录。")

    st.markdown("---")
    st.caption("中学生体质监测与智能分析系统 | Version 1.0 | AI Physical Fitness Monitoring System")
