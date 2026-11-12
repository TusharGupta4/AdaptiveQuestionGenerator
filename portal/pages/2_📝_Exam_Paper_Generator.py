import streamlit as st
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import SessionLocal, Subject, Chapter, ExaminationBlueprint, StudentProfile
from portal.services.paper_generator import PaperGeneratorEngine
from portal.services.adaptive_engine import AdaptivePaperEngine
from portal.services.pdf_export_service import PDFExportService

st.set_page_config(page_title="Exam Studio - Question Paper Generator", page_icon="📝", layout="wide")
st.title("📝 Exam Studio: Question Paper Generator")

db = SessionLocal()

# Active Student context
student_id = st.session_state.get("active_student_id", 1)
active_student = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()

if active_student:
    cur_cls = active_student.academic_class
    is_jee = (cur_cls and (cur_cls.code == "JEE" or "JEE" in cur_cls.grade))
    if is_jee:
        st.info(f"👤 **Student Profile**: {active_student.full_name} | Stream: **JEE Competitive Track**")
    else:
        st.info(f"👤 **Student Profile**: {active_student.full_name} | Grade: **{cur_cls.grade if cur_cls else 'Class 10'}** | Board: **{active_student.board.code if active_student.board else 'CBSE'}**")

gen_mode = st.radio("Select Practice Mode:", ["🎯 Mode 1: Normal Question Paper Practice", "🧠 Mode 2: Adaptive Remedial Question Paper Practice"], horizontal=True)

# ----------------------------------------------------------------------------
# MODE 1: NORMAL QUESTION PAPER GENERATION
# ----------------------------------------------------------------------------
if "Mode 1" in gen_mode:
    st.subheader("Standard Examination Blueprint Generator")
    st.write("Generates question papers adhering to official curriculum guidelines, section structures, and marks distributions.")

    cur_cls = active_student.academic_class if active_student else None
    is_jee = (cur_cls and (cur_cls.code == "JEE" or "JEE" in cur_cls.grade))

    bp_query = db.query(ExaminationBlueprint).filter(ExaminationBlueprint.is_active == True)

    # Strictly filter blueprints by active student's Grade and Board
    if active_student:
        if is_jee:
            # JEE student: filter to JEE blueprints only
            bp_query = bp_query.filter(
                (ExaminationBlueprint.class_id == active_student.class_id) |
                (ExaminationBlueprint.title.ilike("%JEE%"))
            )
        else:
            # School student: filter to exact matching Class and Board
            bp_query = bp_query.filter(
                ExaminationBlueprint.class_id == active_student.class_id,
                ExaminationBlueprint.board_id == active_student.board_id
            )

    filtered_blueprints = bp_query.all()

    c_head, c_chk = st.columns([3, 1])
    with c_chk:
        show_all = st.checkbox("Browse all blueprints", value=False, help="Enable if you want to explore blueprints from other grades or boards")

    if show_all or not filtered_blueprints:
        blueprints = db.query(ExaminationBlueprint).filter(ExaminationBlueprint.is_active == True).all()
        if not filtered_blueprints and active_student:
            st.info("ℹ️ No exact blueprint match found for your current profile. Showing all blueprints.")
    else:
        blueprints = filtered_blueprints

    def format_bp_label(bp):
        s_name = bp.subject.name if (hasattr(bp, "subject") and bp.subject) else "General"
        if show_all:
            b_code = bp.board.code if (hasattr(bp, "board") and bp.board) else ""
            c_code = bp.academic_class.code if (hasattr(bp, "academic_class") and bp.academic_class) else ""
            c_grade = bp.academic_class.grade if (hasattr(bp, "academic_class") and bp.academic_class) else ""
            prefix = "[JEE] " if (c_code == "JEE" or b_code == "JEE") else f"[{b_code} {c_grade}] "
            return f"{prefix}{s_name}: {bp.title} ({bp.total_marks} Marks | {bp.duration_minutes} Mins)"
        else:
            return f"📖 {s_name}: {bp.title} ({bp.total_marks} Marks | {bp.duration_minutes} Mins)"

    bp_dict = {bp.id: format_bp_label(bp) for bp in blueprints}

    col1, col2 = st.columns([2, 1])
    with col1:
        sel_bp_id = st.selectbox(
            "Choose Examination Blueprint:",
            options=list(bp_dict.keys()),
            format_func=lambda x: bp_dict.get(x, "")
        )
    with col2:
        st.write("")
        st.write("")
        gen_btn = st.button("🚀 Generate Blueprint Question Paper", type="primary")

    if gen_btn and sel_bp_id:
        with st.spinner("Selecting questions and assembling balanced test paper..."):
            engine = PaperGeneratorEngine(db)
            paper = engine.generate_blueprint_paper(sel_bp_id, student_id=student_id)
            st.session_state["generated_paper_id"] = paper.id
            st.success(f"🎉 Generated Paper: **{paper.title}** (Paper ID: #{paper.id}) | Total Marks: {paper.total_marks}")

# ----------------------------------------------------------------------------
# MODE 2: ADAPTIVE QUESTION PAPER GENERATION
# ----------------------------------------------------------------------------
else:
    st.subheader("Dynamic Adaptive Question Paper Generator")
    st.write("Analyzes your historical assessment records and dynamically allocates **60%–70% of questions to your weak topics** while maintaining full curriculum coverage.")

    user_board_id = active_student.board_id if active_student else 1
    user_class_id = active_student.class_id if active_student else 2

    avail_subjects = db.query(Subject).filter(
        Subject.board_id == user_board_id,
        Subject.class_id == user_class_id
    ).all()

    if not avail_subjects:
        avail_subjects = db.query(Subject).all()

    s_options = {s.id: s.name for s in avail_subjects}
    c_s, c_q = st.columns([2, 1])
    with c_s:
        sel_subj_id = st.selectbox("Target Subject for Adaptive Practice:", options=list(s_options.keys()), format_func=lambda x: s_options[x])
    with c_q:
        req_q_count = st.slider("Total Questions Required:", min_value=5, max_value=30, value=15, step=5)

    if st.button("🧠 Generate Personalized Adaptive Exam", type="primary"):
        with st.spinner("Analyzing topic mastery scores and calculating remedial quotas..."):
            adapt_engine = AdaptivePaperEngine(db)
            result = adapt_engine.generate_adaptive_paper(
                student_id=student_id,
                subject_id=sel_subj_id,
                total_questions=req_q_count
            )
            paper = result["paper"]
            st.session_state["generated_paper_id"] = paper.id

            st.success(f"🎯 Adaptive Paper Generated: **{paper.title}** (ID: #{paper.id})")
            
            # Display Adaptive Diagnosis Panel
            st.markdown("### 🔍 Adaptive Engine Diagnosis")
            st.info(f"**Pedagogical Rationale:** {result['rationale']}")
            
            if result["weak_topics"]:
                st.warning(f"⚠️ **Targeted Weak Topics (<50% mastery)**: {', '.join(result['weak_topics'])}")
            else:
                st.info("ℹ️ No critical weak topics found. Balanced full-syllabus diagnostic paper assembled.")

# ----------------------------------------------------------------------------
# RENDER GENERATED PAPER & PDF DOWNLOAD
# ----------------------------------------------------------------------------
if "generated_paper_id" in st.session_state:
    from portal.core.database import GeneratedPaper
    cur_paper = db.query(GeneratedPaper).filter(GeneratedPaper.id == st.session_state["generated_paper_id"]).first()
    
    if cur_paper:
        st.markdown("---")
        st.subheader(f"📄 Paper Preview: {cur_paper.title}")
        st.caption(f"Paper ID: #{cur_paper.id} | Total Marks: {cur_paper.total_marks} | Duration: {cur_paper.duration_minutes} Mins")

        # Display Blueprint & Chapter Weightage Compliance Audit
        meta = cur_paper.paper_metadata or {}
        if meta.get("strictly_weightage_compliant"):
            with st.expander("⚖️ Official Weightage & Difficulty Compliance Audit", expanded=False):
                col_d, col_w = st.columns([1, 2])
                with col_d:
                    st.markdown("**Cognitive Difficulty Distribution:**")
                    diff_data = meta.get("difficulty_breakdown", {})
                    for d_k, d_v in diff_data.items():
                        st.write(f"- **{d_k}**: {d_v}%")
                with col_w:
                    st.markdown("**Chapter Marks Allocation vs. Target Weightage:**")
                    audits = meta.get("chapter_weightage_audit", [])
                    if audits:
                        audit_table = [
                            {
                                "Chapter / Unit": a["chapter_name"],
                                "Target Marks": f"{a['target_marks']}m",
                                "Allocated Marks": f"{a['allocated_marks']}m",
                                "Deviation": f"{a['deviation_marks']}m"
                            }
                            for a in audits if a["target_marks"] > 0 or a["allocated_marks"] > 0
                        ]
                        st.dataframe(audit_table, width="stretch")

        # PDF Download Button
        pdf_bytes = PDFExportService.generate_exam_pdf(cur_paper)
        st.download_button(
            label="📥 Download Examination Paper as Printable PDF",
            data=pdf_bytes,
            file_name=f"CollegePur_Exam_Paper_{cur_paper.id}.pdf",
            mime="application/pdf"
        )

        st.markdown("---")
        # Display questions
        for pq in cur_paper.paper_questions:
            q = pq.question
            st.markdown(f"**Q{pq.question_number}.** {q.question_text} `[{pq.allocated_marks} Mark(s)]`")
            
            # Render Diagram if exists
            if q.has_diagram and q.diagram_url:
                local_diag = BASE_DIR / q.diagram_url
                if local_diag.exists():
                    st.image(str(local_diag), width=350, caption=f"Diagram for Q{pq.question_number}")

            if q.options and isinstance(q.options, dict):
                for k, v in q.options.items():
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;**({k})** {v}")
            st.markdown("<br>", unsafe_allow_html=True)

db.close()
