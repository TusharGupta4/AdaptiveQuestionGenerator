import streamlit as st
import plotly.express as px
import pandas as pd
from pathlib import Path
import json

# Backend Services & Models
from app.core.database import SessionLocal
from app.models.taxonomy import Subject, Chapter, Topic
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.paper import GeneratedPaper
from app.models.submission import Student, StudentSubmission, SubmissionStatus
from app.services.ingestion_service import IngestionService
from app.services.paper_generator import PaperGeneratorEngine
from app.services.paper_renderer import PaperRenderer
from app.services.submission_service import SubmissionService
from app.services.evaluation_service import EvaluationService
from app.services.analytics_service import AnalyticsService
from app.services.adaptive_engine import AdaptivePaperEngine
from app.schemas.paper import CustomPaperRequest, SectionRule
from app.schemas.adaptive import AdaptivePaperRequest
from app.schemas.evaluation import SubmissionEvaluationReport, AnswerEvaluationResult, StepEvaluationResult
from app.services.supabase_service import SupabaseService
from app.core.supabase import check_supabase_connection, get_supabase_client

# Page Configuration
st.set_page_config(
    page_title="Adaptive Exam Engine Studio",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 28px; font-weight: bold; color: #1E3A8A; margin-bottom: 5px; }
    .sub-header { font-size: 15px; color: #64748B; margin-bottom: 20px; }
    .metric-card { background-color: #F8FAFC; border-radius: 8px; padding: 15px; border-left: 5px solid #3B82F6; }
    .badge-easy { background-color: #DCFCE7; color: #15803D; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-medium { background-color: #FEF9C3; color: #A16207; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
    .badge-hard { background-color: #FEE2E2; color: #B91C1C; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# Helper DB Session
def get_db():
    return SessionLocal()

# Sidebar Navigation
st.sidebar.title("🎓 Exam Engine")
st.sidebar.markdown("**AI-Powered Adaptive Learning & Evaluation System**")
page = st.sidebar.radio(
    "Go to Module:",
    [
        "📚 Question Bank Explorer",
        "📥 Paper Ingestion Studio",
        "📝 Exam Paper Generator",
        "✍️ Student Submission & OCR",
        "📊 Evaluation & Scorecard",
        "🎯 Knowledge Profile & Adaptive Loop",
        "☁️ Supabase Cloud Hub"
    ]
)

# Supabase Cloud Status Card in Sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("### ☁️ Supabase Cloud")
try:
    supa_info = SupabaseService.get_status()
    if supa_info.get("connected"):
        st.sidebar.success(f"🟢 **Active & Working**\n\n`{supa_info.get('project_ref')}` ({supa_info.get('latency_ms')}ms)")
    else:
        st.sidebar.warning(f"🟡 **Supabase:** {supa_info.get('status', 'Offline')}")
except Exception as e:
    st.sidebar.error(f"🔴 Supabase Status: {e}")

# ------------------------------------------------------------------------------------------
# 1. QUESTION BANK EXPLORER
# ------------------------------------------------------------------------------------------
if page == "📚 Question Bank Explorer":
    st.markdown('<div class="main-header">📚 Hierarchical Question Bank</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Search, filter, and inspect verified questions mapped to syllabus taxonomy</div>', unsafe_allow_html=True)

    db = get_db()
    try:
        col1, col2, col3 = st.columns(3)
        with col1:
            q_types = ["ALL"] + [t.value for t in QuestionType]
            selected_type = st.selectbox("Filter by Question Type", q_types)
        with col2:
            difficulties = ["ALL"] + [d.value for d in DifficultyLevel]
            selected_diff = st.selectbox("Filter by Difficulty", difficulties)
        with col3:
            search_query = st.text_input("Search Question Text", "")

        query = db.query(Question)
        if selected_type != "ALL":
            query = query.filter(Question.question_type == selected_type)
        if selected_diff != "ALL":
            query = query.filter(Question.difficulty == selected_diff)
        if search_query:
            query = query.filter(Question.question_text.ilike(f"%{search_query}%"))

        questions = query.all()
        st.write(f"Showing **{len(questions)}** questions matching criteria:")

        for q in questions:
            with st.expander(f"Q#{q.id} [{q.question_type.value} | {q.marks} Marks | {q.difficulty.value}] - {q.question_text[:70]}..."):
                st.markdown(f"**Question:** {q.question_text}")
                
                # Options if MCQ
                if q.options:
                    st.markdown("**Options:**")
                    for opt in q.options:
                        prefix = "✅ " if opt.is_correct else "⚪ "
                        st.write(f"{prefix} **({opt.option_label})** {opt.option_text}")

                st.markdown(f"**Expected Answer:** `{q.expected_answer}`")
                
                if q.rubric_steps:
                    st.markdown("**Marking Scheme / Rubric:**")
                    steps = q.rubric_steps
                    if isinstance(steps, str):
                        try:
                            steps = json.loads(steps)
                        except Exception:
                            steps = []
                    if isinstance(steps, list):
                        for step in steps:
                            if isinstance(step, dict):
                                st.markdown(f"- {step.get('step')} `[{step.get('marks')} Mark]`")

                st.caption(f"Topic: {q.topic.name if q.topic else 'N/A'} | Chapter: {q.topic.chapter.name if q.topic and q.topic.chapter else 'N/A'}")
    finally:
        db.close()

# ------------------------------------------------------------------------------------------
# 2. INGESTION STUDIO
# ------------------------------------------------------------------------------------------
elif page == "📥 Paper Ingestion Studio":
    st.markdown('<div class="main-header">📥 Ingestion & Taxonomy Pipeline</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload raw question papers (.txt or .pdf) to auto-extract and structure into Question Bank</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload Question Paper Document", type=["txt", "pdf"])
    
    if uploaded_file is not None:
        save_path = Path("data/sample_inputs") / uploaded_file.name
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        st.success(f"File uploaded successfully: `{uploaded_file.name}`")

        if st.button("🚀 Run Ingestion & Structuring Pipeline", type="primary"):
            with st.spinner("Extracting questions, parsing rubrics, and matching syllabus hierarchy..."):
                db = get_db()
                try:
                    service = IngestionService(db)
                    count = service.ingest_file(str(save_path))
                    st.balloons()
                    st.success(f"🎉 Successfully extracted and persisted **{count} questions** into Question Bank!")
                except Exception as e:
                    st.error(f"Error during ingestion: {e}")
                finally:
                    db.close()

# ------------------------------------------------------------------------------------------
# 3. EXAM PAPER GENERATOR
# ------------------------------------------------------------------------------------------
elif page == "📝 Exam Paper Generator":
    st.markdown('<div class="main-header">📝 Question Paper Generation Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Generate blueprint-validated papers with strict mathematical mark constraints</div>', unsafe_allow_html=True)

    db = get_db()
    try:
        subjects = db.query(Subject).all()
        if not subjects:
            st.warning("Please initialize database or ingest questions first.")
        else:
            sub_map = {f"{s.name} ({s.grade})": s.id for s in subjects}
            selected_sub_name = st.selectbox("Select Subject", list(sub_map.keys()))
            subject_id = sub_map[selected_sub_name]

            mode = st.radio("Paper Generation Mode", ["Standard Exam Template", "Custom Blueprint"], horizontal=True)

            if mode == "Standard Exam Template":
                template = st.selectbox("Exam Pattern Blueprint", ["QUICK_TEST_10 (8-10 Marks Standard Unit Test)"])
                if st.button("⚡ Generate Standard Paper", type="primary"):
                    engine = PaperGeneratorEngine(db)
                    result = engine.generate_standard_paper(subject_id, "QUICK_TEST_10")
                    html_file = PaperRenderer.render_to_html(result)
                    st.success(f"✅ Generated Paper #{result.paper_id}: **{result.title}** ({result.total_marks} Marks)")
                    st.markdown(f"**Printable HTML ready at:** `{html_file}`")

                    # Preview
                    if Path(html_file).exists():
                        with open(html_file, "r", encoding="utf-8") as f:
                            html_content = f.read()
                            st.components.v1.html(html_content, height=450, scrolling=True)
                            st.download_button(
                                "📥 Download Paper HTML",
                                html_content,
                                file_name=f"paper_{result.paper_id}.html",
                                mime="text/html",
                                key=f"dl_std_{result.paper_id}"
                            )

            else:
                title = st.text_input("Exam Title", "Class 10 CBSE Custom Mathematics Assessment")
                total_marks = st.number_input("Target Total Marks Constraint", min_value=1.0, max_value=80.0, value=5.0, step=1.0)
                duration = st.slider("Exam Duration (Minutes)", 15, 180, 30)

                st.subheader("Section Configuration")
                col1, col2 = st.columns(2)
                with col1:
                    mcq_count = st.number_input("Section A (1-Mark MCQs) Count", min_value=0, max_value=20, value=1)
                with col2:
                    short_count = st.number_input("Section B (2-Mark Short) Count", min_value=0, max_value=20, value=2)

                calculated = (mcq_count * 1.0) + (short_count * 2.0)
                if abs(calculated - total_marks) > 0.01:
                    st.error(f"⚠️ Constraint Mismatch: Configured sections sum to **{calculated} marks**, but target is **{total_marks} marks**.")
                else:
                    st.info(f"✅ Mark Constraint Satisfied: {calculated} / {total_marks} marks.")

                    if st.button("🚀 Generate Custom Paper", type="primary"):
                        req = CustomPaperRequest(
                            title=title,
                            subject_id=subject_id,
                            total_marks=total_marks,
                            duration_minutes=duration,
                            sections=[
                                SectionRule(section_name="Section A (Objective)", question_type=QuestionType.MCQ, marks_per_question=1.0, question_count=mcq_count),
                                SectionRule(section_name="Section B (Short Answer)", question_type=QuestionType.SHORT, marks_per_question=2.0, question_count=short_count)
                            ]
                        )
                        engine = PaperGeneratorEngine(db)
                        result = engine.generate_custom_paper(req)
                        html_file = PaperRenderer.render_to_html(result)
                        st.success(f"🎉 Custom Paper Generated: ID #{result.paper_id}")
                        if Path(html_file).exists():
                            with open(html_file, "r", encoding="utf-8") as f:
                                html_content = f.read()
                                st.components.v1.html(html_content, height=450, scrolling=True)
                                st.download_button(
                                    "📥 Download Paper HTML",
                                    html_content,
                                    file_name=f"paper_{result.paper_id}.html",
                                    mime="text/html",
                                    key=f"dl_cust_{result.paper_id}"
                                )
    finally:
        db.close()

# ------------------------------------------------------------------------------------------
# 4. STUDENT SUBMISSION & OCR
# ------------------------------------------------------------------------------------------
elif page == "✍️ Student Submission & OCR":
    st.markdown('<div class="main-header">✍️ Student Answer Sheet Submission & OCR</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Upload student responses, extract text via OCR, and auto-segment by question number</div>', unsafe_allow_html=True)

    db = get_db()
    try:
        papers = db.query(GeneratedPaper).all()
        if not papers:
            st.warning("No papers generated yet! Go to Paper Generator first.")
        else:
            paper_options = {f"Paper #{p.id}: {p.title} ({p.total_marks} Marks)": p.id for p in papers}
            selected_paper = st.selectbox("Select Exam Paper", list(paper_options.keys()))
            paper_id = paper_options[selected_paper]

            col1, col2 = st.columns(2)
            with col1:
                student_name = st.text_input("Student Name", "Aryan Sharma")
            with col2:
                roll_no = st.text_input("Roll Number", "CBSE-10-9842")

            uploaded_sheet = st.file_uploader("Upload Answer Sheet (Scanned TXT / Image / PDF)", type=["txt", "pdf", "jpg", "png"])

            if uploaded_sheet is not None:
                save_dest = Path("data/submissions") / f"{roll_no}_{uploaded_sheet.name}"
                save_dest.parent.mkdir(parents=True, exist_ok=True)
                with open(save_dest, "wb") as f:
                    f.write(uploaded_sheet.getbuffer())

                if st.button("🔍 Process OCR & Segment Answers", type="primary"):
                    service = SubmissionService(db)
                    sub_res = service.process_submission(
                        paper_id=paper_id,
                        student_roll=roll_no,
                        student_name=student_name,
                        file_path=str(save_dest)
                    )

                    st.success(f"✅ Successfully Segmented Submission #{sub_res.submission_id}!")
                    st.write(f"Extracted **{sub_res.total_answers_extracted} answers** from sheet:")

                    for ans in sub_res.answers:
                        with st.expander(f"Q{ans.question_number} [Target: {ans.marks_allocated} Marks] - {ans.question_text[:50]}..."):
                            st.text_area(
                                "Extracted Student Answer",
                                ans.student_answer_text,
                                height=100,
                                disabled=True,
                                key=f"ans_review_{sub_res.submission_id}_{ans.question_number}"
                            )
    finally:
        db.close()

# ------------------------------------------------------------------------------------------
# 5. EVALUATION & SCORECARD
# ------------------------------------------------------------------------------------------
elif page == "📊 Evaluation & Scorecard":
    st.markdown('<div class="main-header">📊 Multi-Criteria Rubric Evaluation</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Step-by-step partial credit scoring, formula checks, and constructive feedback</div>', unsafe_allow_html=True)

    db = get_db()
    try:
        submissions = db.query(StudentSubmission).all()
        if not submissions:
            st.warning("No submissions found to evaluate.")
        else:
            sub_options = {f"Submission #{s.id} - {s.student.name} ({s.paper.title})": s.id for s in submissions}
            selected_sub = st.selectbox("Select Submission to Grade", list(sub_options.keys()))
            submission_id = sub_options[selected_sub]

            sub_obj = db.query(StudentSubmission).filter(StudentSubmission.id == submission_id).first()
            is_evaluated = sub_obj is not None and sub_obj.status == SubmissionStatus.EVALUATED

            col_btn, col_status = st.columns([2, 3])
            with col_btn:
                btn_label = "🔄 Re-Run Rubric Evaluation" if is_evaluated else "⚖️ Run Rubric Evaluation"
                run_eval = st.button(btn_label, type="primary")

            with col_status:
                if is_evaluated:
                    st.success(f"Status: Evaluated | Score: {sub_obj.total_score} Marks")
                else:
                    st.info("Status: Pending Evaluation")

            report = None
            if run_eval:
                with st.spinner("Evaluating student answers against rubrics and marking schemes..."):
                    eval_service = EvaluationService(db)
                    report = eval_service.evaluate_submission(submission_id)
            elif is_evaluated and sub_obj:
                total_possible = sum(sa.question.marks for sa in sub_obj.answers) if sub_obj.answers else 0.0
                total_awarded = sub_obj.total_score or 0.0
                percentage = round((total_awarded / total_possible * 100), 2) if total_possible > 0 else 0.0

                detailed = []
                for sa in sub_obj.answers:
                    step_evals = []
                    if sa.step_scores:
                        try:
                            parsed_steps = json.loads(sa.step_scores)
                            step_evals = [StepEvaluationResult(**s) for s in parsed_steps]
                        except Exception:
                            step_evals = []
                    detailed.append(AnswerEvaluationResult(
                        question_number=sa.question_number,
                        question_id=sa.question_id,
                        question_type=sa.question.question_type.value,
                        max_marks=sa.question.marks,
                        marks_awarded=sa.marks_awarded or 0.0,
                        feedback=sa.feedback or "Evaluated",
                        step_evaluations=step_evals
                    ))

                report = SubmissionEvaluationReport(
                    submission_id=sub_obj.id,
                    student_name=sub_obj.student.name,
                    roll_number=sub_obj.student.roll_number,
                    paper_title=sub_obj.paper.title,
                    total_paper_marks=round(total_possible, 2),
                    total_score_obtained=round(total_awarded, 2),
                    percentage=percentage,
                    status=sub_obj.status.value,
                    detailed_answers=detailed
                )

            if report:
                # Scorecard Banner
                st.markdown("### 🏆 Official Examination Scorecard")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Student", report.student_name)
                c2.metric("Total Paper Marks", f"{report.total_paper_marks} M")
                c3.metric("Marks Awarded", f"{report.total_score_obtained} M")
                c4.metric("Percentage", f"{report.percentage}%")

                st.divider()

                # Detailed Step Breakdown
                st.subheader("Question-Wise Step-Marking Breakdown")
                for ans in report.detailed_answers:
                    with st.expander(f"Q{ans.question_number} ({ans.question_type}) - Score: {ans.marks_awarded} / {ans.max_marks} Marks"):
                        st.info(f"**Feedback:** {ans.feedback}")
                        if ans.step_evaluations:
                            st.write("**Rubric Steps Evaluation:**")
                            for s in ans.step_evaluations:
                                icon = "✅" if s.is_satisfied else "❌"
                                st.write(f"{icon} **{s.step_description}**: `{s.marks_awarded} / {s.max_marks} Marks` — _{s.reasoning}_")
            elif not is_evaluated:
                st.info("Click 'Run Rubric Evaluation' above to grade this submission against mark scheme and rubrics.")
    finally:
        db.close()

# ------------------------------------------------------------------------------------------
# 6. KNOWLEDGE PROFILE & ADAPTIVE LOOP
# ------------------------------------------------------------------------------------------
elif page == "🎯 Knowledge Profile & Adaptive Loop":
    st.markdown('<div class="main-header">🎯 Student Knowledge Matrix & Adaptive Engine</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Pedagogical analytics bridge connecting evaluation results to personalized remedial exams</div>', unsafe_allow_html=True)

    db = get_db()
    try:
        students = db.query(Student).all()
        if not students:
            st.warning("No students found.")
        else:
            student_map = {f"{s.name} ({s.roll_number})": s.id for s in students}
            selected_student_name = st.selectbox("Select Student", list(student_map.keys()))
            student_id = student_map[selected_student_name]

            analytics_service = AnalyticsService(db)
            try:
                profile = analytics_service.generate_student_profile(student_id)

                # Top Metrics
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Overall Mastery", f"{profile.overall_accuracy}%")
                m2.metric("Questions Attempted", profile.total_questions_attempted)
                m3.metric("Strong Topics", len(profile.strong_topics))
                m4.metric("Weak Topics", len(profile.weak_topics))

                st.divider()

                # Plotly Chart
                st.subheader("Topic Mastery Performance Matrix")
                chart_data = []
                for t in profile.topic_performance:
                    chart_data.append({
                        "Topic": t.topic_name,
                        "Chapter": t.chapter_name,
                        "Accuracy (%)": t.accuracy_percentage,
                        "Status": t.status.value if hasattr(t.status, 'value') else str(t.status)
                    })
                df = pd.DataFrame(chart_data)

                if not df.empty:
                    color_map = {"STRONG": "#10B981", "MODERATE": "#F59E0B", "WEAK": "#EF4444"}
                    fig = px.bar(
                        df,
                        x="Accuracy (%)",
                        y="Topic",
                        color="Status",
                        color_discrete_map=color_map,
                        orientation="h",
                        text="Accuracy (%)",
                        hover_data=["Chapter"],
                        title="Student Concept Mastery by Topic"
                    )
                    fig.update_layout(yaxis=dict(autorange="reversed"))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No topic mastery records available yet.")

                # Pedagogical Advice
                st.subheader("💡 Automated Diagnostic Recommendations")
                for rec in profile.recommendations:
                    st.warning(rec)

                st.divider()

                # THE ADAPTIVE LOOP TRIGGER
                st.subheader("⚡ Closed-Loop: Generate Personalized Adaptive Remedial Exam")
                st.write(
                    f"The engine will prioritize student's weak topics "
                    f"(**{', '.join(profile.weak_topics) if profile.weak_topics else 'all topics'}**) "
                    f"to formulate targeted practice."
                )

                col_a, col_b = st.columns(2)
                with col_a:
                    adaptive_marks = st.number_input("Adaptive Test Marks", min_value=2.0, max_value=20.0, value=5.0, step=1.0)
                with col_b:
                    adaptive_mode = st.selectbox("Adaptive Mode", ["REMEDIAL (Focus on Weak Concepts)", "CHALLENGE (Advanced)"])

                if st.button("🎯 Generate Tailored Adaptive Exam", type="primary"):
                    adaptive_engine = AdaptivePaperEngine(db)
                    req = AdaptivePaperRequest(
                        student_id=student_id,
                        title=f"Personalized Remedial Math Exam",
                        total_marks=adaptive_marks,
                        duration_minutes=25,
                        focus_mode="REMEDIAL" if "REMEDIAL" in adaptive_mode else "CHALLENGE"
                    )
                    adaptive_res = adaptive_engine.generate_adaptive_paper(req)

                    st.balloons()
                    st.success(f"🎉 Generated Adaptive Paper #{adaptive_res.paper_details.paper_id} for {adaptive_res.student_name}!")
                    st.info(f"**Pedagogical Rationale:** {adaptive_res.pedagogical_rationale}")

                    st.write("**Adaptive Topic Allocations:**")
                    for alloc in adaptive_res.topic_allocation_summary:
                        st.markdown(f"- **{alloc.topic_name}** `[{alloc.status}]`: {alloc.questions_count} questions ({alloc.allocated_marks} Marks)")

                    html_file = Path(f"data/generated_papers/paper_{adaptive_res.paper_details.paper_id}.html")
                    if html_file.exists():
                        with open(html_file, "r", encoding="utf-8") as f:
                            html_text = f.read()
                            st.components.v1.html(html_text, height=450, scrolling=True)
                            st.download_button(
                                "📥 Download Adaptive Paper HTML",
                                html_text,
                                file_name=f"adaptive_paper_{adaptive_res.paper_details.paper_id}.html",
                                mime="text/html",
                                key=f"dl_adapt_{adaptive_res.paper_details.paper_id}"
                            )

            except Exception as e:
                st.info(f"Could not build profile yet: {e}. Please submit and evaluate an answer sheet first.")
    finally:
        db.close()

# ------------------------------------------------------------------------------------------
# 7. SUPABASE CLOUD HUB
# ------------------------------------------------------------------------------------------
elif page == "☁️ Supabase Cloud Hub":
    st.markdown('<div class="main-header">☁️ Supabase Cloud Integration Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Live connection monitoring, Cloud Storage management, and database synchronization</div>', unsafe_allow_html=True)

    status_data = SupabaseService.get_status()

    # Top Status Banner
    if status_data.get("connected"):
        st.success(f"✅ **Supabase Cloud is Active and Connected!** Project: `{status_data.get('project_ref')}` | Network Latency: `{status_data.get('latency_ms')} ms`")
    else:
        st.error(f"❌ **Supabase Connection Issue:** {status_data.get('message')}")

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            label="Connection Status",
            value="ACTIVE" if status_data.get("connected") else "OFFLINE"
        )
    with m2:
        st.metric(
            label="Auth Service (GoTrue)",
            value=status_data.get("auth_status", "UNKNOWN")
        )
    with m3:
        st.metric(
            label="Storage Service",
            value=status_data.get("storage_status", "UNKNOWN")
        )
    with m4:
        st.metric(
            label="Ping Latency",
            value=f"{status_data.get('latency_ms', 'N/A')} ms"
        )

    tab_diag, tab_storage, tab_db_sync = st.tabs(["🔍 Diagnostics & Health", "📦 Cloud Storage Assets", "🔄 Database & Backup"])

    with tab_diag:
        st.subheader("Cloud Connection Details")
        st.json(status_data)

        if st.button("🔄 Re-test Supabase Connection Now"):
            st.rerun()

    with tab_storage:
        st.subheader("📦 Supabase Cloud Storage Buckets")
        buckets = status_data.get("buckets", [])
        if buckets:
            st.write(f"Active Buckets: **{', '.join(buckets)}**")
        else:
            st.info("No custom storage buckets found yet. Buckets created in your Supabase dashboard (Storage) will appear here.")

        st.markdown("#### 📤 Upload Generated Papers to Supabase Storage")
        papers_dir = Path("data/generated_papers")
        if papers_dir.exists():
            html_files = list(papers_dir.glob("*.html"))
            if html_files:
                selected_file = st.selectbox("Select Generated Exam Paper HTML", [f.name for f in html_files])
                target_bucket = st.text_input("Target Storage Bucket Name", value="exam-papers")
                if st.button("🚀 Upload Paper to Supabase Cloud Storage"):
                    with open(papers_dir / selected_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    res = SupabaseService.upload_file_to_storage(
                        bucket_name=target_bucket,
                        destination_path=f"papers/{selected_file}",
                        file_bytes=content.encode("utf-8"),
                        content_type="text/html"
                    )
                    if res.get("success"):
                        st.success(f"Uploaded successfully! Public URL: {res.get('public_url')}")
                    else:
                        st.warning(f"Upload response: {res.get('error')}. {res.get('hint', '')}")
            else:
                st.write("No generated papers found in `data/generated_papers/` yet. Generate one in Module 3!")
        else:
            st.write("No `data/generated_papers/` directory found.")

    with tab_db_sync:
        st.subheader("Database Configuration & Question Bank Sync")
        from app.core.database import db_url
        st.write(f"**Current SQLAlchemy Engine:** `{db_url}`")

        db = get_db()
        try:
            total_questions = db.query(Question).count()
            total_subjects = db.query(Subject).count()
            st.markdown(f"- **Local Question Bank Count:** `{total_questions}` questions across `{total_subjects}` syllabus subjects.")
        finally:
            db.close()

        st.markdown("""
        > [!TIP]
        > **Switching to Supabase PostgreSQL:**
        > To use Supabase's hosted Postgres database directly for all questions and papers, add your Supabase PostgreSQL connection string in `.env`:
        > ```env
        > DATABASE_URL=postgresql://postgres.nfszfnjsrhmobjikliqk:[YOUR-PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres
        > ```
        > The engine will automatically detect PostgreSQL, enable connection pooling, and create all schema tables on startup.
        """)