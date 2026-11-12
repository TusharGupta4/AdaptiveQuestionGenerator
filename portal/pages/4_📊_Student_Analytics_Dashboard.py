import streamlit as st
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import SessionLocal, StudentProfile, StudentSubmission, StudentTopicMastery, GeneratedPaper

st.set_page_config(page_title="Student Analytics Dashboard", page_icon="📊", layout="wide")
st.title("📊 Student Performance & Mastery Dashboard")

db = SessionLocal()
student_id = st.session_state.get("active_student_id", 1)
active_student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()

if active_student:
    st.markdown(f"### Student: **{active_student.full_name}** (`{active_student.email}`)")
    cur_cls = active_student.academic_class
    is_jee = (cur_cls and (cur_cls.code == "JEE" or "JEE" in cur_cls.grade))
    if is_jee:
        st.caption("Enrolled Stream: **JEE Competitive Track**")
    else:
        st.caption(f"Current Grade: **{cur_cls.grade if cur_cls else 'Class 10'}** | Enrolled Board: **{active_student.board.code if active_student.board else 'CBSE'}**")

# 1. Macro Metrics
submissions = db.query(StudentSubmission).filter(StudentSubmission.student_id == student_id).all()
total_attempts = len(submissions)
avg_score = round(sum(float(s.accuracy_percent or 0.0) for s in submissions) / total_attempts, 1) if total_attempts > 0 else 0.0

mastery_records = db.query(StudentTopicMastery).filter(StudentTopicMastery.student_id == student_id).all()
weak_count = sum(1 for m in mastery_records if m.mastery_status == "Needs Improvement")
strong_count = sum(1 for m in mastery_records if m.mastery_status == "Strong")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Assessments Completed", f"{total_attempts}")
m2.metric("Cumulative Accuracy", f"{avg_score}%")
m3.metric("Weak Topics (<50%)", f"{weak_count} ⚠️", delta=-weak_count if weak_count > 0 else None, delta_color="inverse")
m4.metric("Mastered Topics (≥80%)", f"{strong_count} 🏆", delta=strong_count)

st.markdown("---")

# 2. Topic Mastery Badges
st.subheader("🎯 Topic-Wise Skill Mastery Breakdown")
st.write("The Adaptive Assessment Engine uses these real-time scores to continuously prioritize weak chapters in your upcoming exams.")

c_weak, c_avg, c_strong = st.columns(3)

with c_weak:
    st.markdown("#### 🔴 Needs Improvement (<50%)")
    weaks = [m for m in mastery_records if m.mastery_status == "Needs Improvement"]
    if weaks:
        for w in weaks:
            st.error(f"**{w.chapter_name}**: {w.accuracy_percentage}% ({w.marks_obtained}/{w.marks_possible} Marks)")
        if st.button("🚀 Generate Adaptive Test for Weak Topics", type="primary"):
            st.switch_page("pages/2_📝_Exam_Paper_Generator.py")
    else:
        st.info("No critical weak topics detected. Great job!")

with c_avg:
    st.markdown("#### 🟡 Developing (50% - 79%)")
    avgs = [m for m in mastery_records if m.mastery_status == "Average"]
    if avgs:
        for a in avgs:
            st.warning(f"**{a.chapter_name}**: {a.accuracy_percentage}% ({a.marks_obtained}/{a.marks_possible} Marks)")
    else:
        st.write("No topics currently in intermediate range.")

with c_strong:
    st.markdown("#### 🟢 Mastered (≥80%)")
    strongs = [m for m in mastery_records if m.mastery_status == "Strong"]
    if strongs:
        for s in strongs:
            st.success(f"**{s.chapter_name}**: {s.accuracy_percentage}% ({s.marks_obtained}/{s.marks_possible} Marks)")
    else:
        st.write("Keep practicing to unlock mastered topics!")

st.markdown("---")

# 3. Assessment History Table
st.subheader("📜 Previous Assessment Attempts")
if submissions:
    hist_data = []
    for s in reversed(submissions):
        paper_title = s.paper.title if s.paper else f"Paper #{s.paper_id}"
        hist_data.append({
            "Submission ID": f"#{s.id}",
            "Exam Paper Title": paper_title,
            "Format": s.submission_type,
            "Score": f"{s.total_score} Marks",
            "Accuracy": f"{s.accuracy_percent}%",
            "Date Submitted": s.created_at.strftime("%Y-%m-%d %H:%M") if s.created_at else "Recent"
        })
    st.dataframe(hist_data, width="stretch")
else:
    st.info("No completed assessments yet. Head over to **Exam Studio** to generate and attempt your first paper!")

db.close()
