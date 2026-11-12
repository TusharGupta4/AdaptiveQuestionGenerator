import streamlit as st
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import SessionLocal, Board, AcademicClass, StudentProfile, Question, Subject, Chapter, GeneratedPaper

st.set_page_config(
    page_title="CollegePur - Unified Assessment Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-title { font-size: 32px; font-weight: 800; color: #1E3A8A; margin-bottom: 5px; }
    .subtitle { font-size: 16px; color: #4B5563; margin-bottom: 25px; }
    .card { background-color: #F8FAFC; border-radius: 10px; padding: 18px; border: 1px solid #E2E8F0; }
    .badge { padding: 4px 10px; border-radius: 6px; font-weight: bold; font-size: 13px; }
    .badge-blue { background-color: #EFF6FF; color: #1D4ED8; }
</style>
""", unsafe_allow_html=True)

# Database Session
db = SessionLocal()

# ----------------------------------------------------------------------------
# SIDEBAR: PERSISTENT STUDENT PROFILE (Zero Re-Selection Required)
# ----------------------------------------------------------------------------
st.sidebar.image("https://img.icons8.com/color/96/graduation-cap.png", width=60)
st.sidebar.title("CollegePur Portal")
st.sidebar.markdown("**AI-Powered Adaptive Assessment Ecosystem**")
st.sidebar.markdown("---")

students = db.query(StudentProfile).all()
boards = db.query(Board).all()
classes = db.query(AcademicClass).all()

board_map = {b.id: b.code for b in boards}
board_by_code = {b.code: b for b in boards}
class_by_code = {c.code: c for c in classes}

grade_code_to_label = {
    "9": "Grade 9",
    "10": "Grade 10",
    "11": "Grade 11",
    "12": "Grade 12",
    "JEE": "JEE"
}
grade_label_to_code = {v: k for k, v in grade_code_to_label.items()}

if "active_student_id" not in st.session_state and students:
    st.session_state["active_student_id"] = students[0].id

student_options = {s.id: f"{s.full_name} ({s.email})" for s in students}
selected_sid = st.sidebar.selectbox(
    "👤 Active Student Profile:",
    options=list(student_options.keys()),
    format_func=lambda x: student_options.get(x, "Unknown"),
    index=0 if students else None
)

if selected_sid:
    active_student = db.query(StudentProfile).filter(StudentProfile.id == selected_sid).first()
    st.session_state["active_student"] = active_student
    st.session_state["active_student_id"] = active_student.id
    st.session_state["board_id"] = active_student.board_id
    st.session_state["class_id"] = active_student.class_id

    cur_cls = db.query(AcademicClass).filter(AcademicClass.id == active_student.class_id).first() if active_student else None
    cur_brd = db.query(Board).filter(Board.id == active_student.board_id).first() if active_student else None
    cur_grade_label = grade_code_to_label.get(cur_cls.code, "Grade 10") if cur_cls else "Grade 10"

    if cur_grade_label == "JEE":
        st.sidebar.info(
            "🎯 **Current Grade:** JEE\n\n"
            "*(Board is not applicable for JEE)*"
        )
    else:
        st.sidebar.info(
            f"🎯 **Current Grade:** {cur_grade_label}\n\n"
            f"🏛️ **Preferred Board:** {cur_brd.code if cur_brd else 'CBSE'}"
        )

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ Edit Profile / Switch Stream"):
    new_name = st.text_input("Name", value=active_student.full_name if active_student else "")
    new_email = st.text_input("Email", value=active_student.email if active_student else "")

    # 1. Ask Current Grade FIRST (Available options: Grade 9, Grade 10, Grade 11, Grade 12, JEE)
    grade_options = ["Grade 9", "Grade 10", "Grade 11", "Grade 12", "JEE"]
    def_grade_idx = grade_options.index(cur_grade_label) if cur_grade_label in grade_options else 1
    selected_grade = st.selectbox("Current Grade", options=grade_options, index=def_grade_idx)

    # 2. Dynamic Board Selection based on Grade
    selected_board_code = None
    if selected_grade == "JEE":
        # Skipped / Hidden completely for JEE
        st.caption("ℹ️ Board selection is not applicable for JEE.")
    elif selected_grade in ["Grade 9", "Grade 10"]:
        # Only CBSE and ICSE
        board_opts = ["CBSE", "ICSE"]
        def_b_idx = 0
        if cur_brd and cur_brd.code in board_opts:
            def_b_idx = board_opts.index(cur_brd.code)
        selected_board_code = st.selectbox("Preferred Board", options=board_opts, index=def_b_idx)
    elif selected_grade in ["Grade 11", "Grade 12"]:
        # Only CBSE and ISC
        board_opts = ["CBSE", "ISC"]
        def_b_idx = 0
        if cur_brd and cur_brd.code in board_opts:
            def_b_idx = board_opts.index(cur_brd.code)
        selected_board_code = st.selectbox("Preferred Board", options=board_opts, index=def_b_idx)

    if st.button("Save Profile Settings", type="primary"):
        if active_student:
            target_class_code = grade_label_to_code.get(selected_grade, "10")
            cls_obj = class_by_code.get(target_class_code)

            active_student.full_name = new_name
            active_student.email = new_email
            if cls_obj:
                active_student.class_id = cls_obj.id

            if selected_grade == "JEE":
                jee_b = board_by_code.get("JEE")
                active_student.board_id = jee_b.id if jee_b else None
            else:
                brd_obj = board_by_code.get(selected_board_code)
                if brd_obj:
                    active_student.board_id = brd_obj.id

            db.commit()
            st.success("Profile updated! Question papers will auto-adapt to this grade and stream.")
            st.rerun()

# ----------------------------------------------------------------------------
# MAIN DASHBOARD LANDING
# ----------------------------------------------------------------------------
st.markdown("<div class='main-title'>🎓 CollegePur Adaptive Learning & Assessment Hub</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Unified Question Paper Generation, Multimodal Handwritten Evaluation & Dynamic Remedial Analytics</div>", unsafe_allow_html=True)

# Metrics
total_questions = db.query(Question).count()
total_subjects = db.query(Subject).count()
total_chapters = db.query(Chapter).count()
total_papers = db.query(GeneratedPaper).count()

col1, col2, col3, col4 = st.columns(4)
col1.metric("📚 Total Questions Ingested", f"{total_questions:,}")
col2.metric("📖 Academic Subjects", f"{total_subjects}")
col3.metric("📑 Curriculum Chapters", f"{total_chapters}")
col4.metric("📝 Papers Generated", f"{total_papers}")

st.markdown("---")
st.subheader("🚀 Quick Launch Assessment Modules")

c1, c2, c3 = st.columns(3)

with c1:
    st.markdown("""
    <div class='card'>
        <h3>📥 1. Question Bank & Ingestion</h3>
        <p>Upload question paper PDFs (JEE or Classes 9–12), extract questions via OCR, or bulk-import CSV/Excel question banks.</p>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class='card'>
        <h3>📝 2. Exam Studio & Generator</h3>
        <p>Generate standard Blueprint practice exams or personalized <b>Adaptive Papers</b> targeting your weak topics with instant PDF downloads.</p>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class='card'>
        <h3>✍️ 3. Attempt & Evaluator</h3>
        <p>Take tests online (JEE MCQs) or upload handwritten answer sheets for automated rubric-based grading and feedback.</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")
st.info("💡 **Navigation Tip**: Use the left sidebar to navigate to any module: `Question Bank`, `Exam Generator`, `Attempt & Evaluate`, or `Analytics Dashboard`.")

db.close()
