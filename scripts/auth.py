import streamlit as st
from scripts.db_utils import init_db, register_student, verify_student_login

TEACHER_ACCOUNTS = {
    "teacher": "123456"
}


def init_session():
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "role" not in st.session_state:
        st.session_state.role = None
    if "username" not in st.session_state:
        st.session_state.username = None


def login_page():
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    st.title("中学生体质监测与智能分析系统")
    st.caption("请输入账号信息登录系统，或在学生端完成注册")

    tab1, tab2 = st.tabs(["登录", "学生注册"])

    # =========================
    # 登录页
    # =========================
    with tab1:
        _, center, _ = st.columns([1, 1.2, 1])

        with center:
            st.subheader("用户登录")

            role = st.selectbox("请选择身份", ["教师", "学生"])
            username = st.text_input("账号")
            password = st.text_input("密码", type="password")

            if st.button("登录", use_container_width=True):
                username = str(username).strip()
                password = str(password).strip()

                if not username or not password:
                    st.warning("请输入账号和密码")
                    st.stop()

                if role == "教师":
                    if username in TEACHER_ACCOUNTS and TEACHER_ACCOUNTS[username] == password:
                        st.session_state.logged_in = True
                        st.session_state.role = "教师"
                        st.session_state.username = username
                        st.success("教师登录成功")
                        st.rerun()
                    else:
                        st.error("教师账号或密码错误")

                elif role == "学生":
                    login_ok, student_info = verify_student_login(username.zfill(3), password)

                    if login_ok:
                        st.session_state.logged_in = True
                        st.session_state.role = "学生"
                        # 学生端后续页面统一拿学号作为 username 使用
                        st.session_state.username = str(student_info.get("student_id", username)).zfill(3)
                        st.success("学生登录成功")
                        st.rerun()
                    else:
                        st.error("学生账号或密码错误，或尚未注册")

    # =========================
    # 学生注册页
    # =========================
    with tab2:
        _, center2, _ = st.columns([1, 1.4, 1])

        with center2:
            st.subheader("学生信息注册")

            student_id = st.text_input("学号")
            password = st.text_input("设置密码", type="password", key="reg_password")
            name = st.text_input("姓名")
            gender = st.selectbox("性别", ["男", "女"])
            age = st.number_input("年龄", min_value=10, max_value=25, value=15)
            class_name = st.text_input("班级")
            phone = st.text_input("联系电话")

            if st.button("提交注册", use_container_width=True):
                student_id = str(student_id).strip().zfill(3)
                password = str(password).strip()
                name = str(name).strip()
                class_name = str(class_name).strip()
                phone = str(phone).strip()

                if not student_id or not password or not name:
                    st.warning("请完整填写学号、密码、姓名")
                    st.stop()

                ok, msg = register_student(
                    student_id=student_id,
                    password=password,
                    name=name,
                    gender=gender,
                    age=int(age),
                    class_name=class_name,
                    phone=phone
                )

                if ok:
                    st.success(msg)
                else:
                    st.error(msg)


def logout_button():
    if st.sidebar.button("退出登录", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.username = None
        st.rerun()
