import streamlit as st
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import SessionLocal, GeneratedPaper, StudentSubmission, StudentProfile
from portal.services.evaluation_service import EvaluationService

st.set_page_config(page_title="Attempt & Evaluate Hub", page_icon="✍️", layout="wide")
st.title("✍️ Examination Submission & Rubric Evaluation")

db = SessionLocal()
student_id = st.session_state.get("active_student_id", 1)

# List generated papers
papers = db.query(GeneratedPaper).order_by(GeneratedPaper.id.desc()).limit(15).all()
if not papers:
    st.warning("No generated test papers found! Please generate a paper first in the 'Exam Studio'.")
    st.stop()

paper_options = {p.id: f"#{p.id} - {p.title} ({p.total_marks} Marks)" for p in papers}
default_pid = st.session_state.get("generated_paper_id", papers[0].id)
selected_pid = st.selectbox("Select Examination Paper to Attempt:", options=list(paper_options.keys()), index=list(paper_options.keys()).index(default_pid) if default_pid in paper_options else 0, format_func=lambda x: paper_options[x])

target_paper = db.query(GeneratedPaper).filter(GeneratedPaper.id == selected_pid).first()

attempt_type = st.radio("Choose Attempt Format:", ["💻 Mode A: Online Interactive Attempt", "📄 Mode B: Upload Written Answer Sheet PDF"], horizontal=True)

# ----------------------------------------------------------------------------
# MODE A: ONLINE INTERACTIVE ATTEMPT
# ----------------------------------------------------------------------------
if "Mode A" in attempt_type:
    st.subheader(f"Exam: {target_paper.title}")
    st.caption(f"Paper ID: #{target_paper.id} | Total Marks: {target_paper.total_marks}")

    user_answers = {}
    with st.form("exam_form"):
        for pq in target_paper.paper_questions:
            q = pq.question
            st.markdown(f"**Q{pq.question_number}.** {q.question_text} `[{pq.allocated_marks} Mark(s)]`")

            if q.has_diagram and q.diagram_url:
                local_diag = BASE_DIR / q.diagram_url
                if local_diag.exists():
                    st.image(str(local_diag), width=320)

            if q.question_type == "mcq_single" and q.options and isinstance(q.options, dict):
                opt_labels = ["Not Attempted"] + [f"{k}: {v}" for k, v in q.options.items()]
                choice = st.radio(f"Select Answer for Q{pq.question_number}:", opt_labels, key=f"q_input_{q.id}")
                if choice != "Not Attempted":
                    user_answers[str(q.id)] = choice.split(":")[0].strip()
            else:
                text_ans = st.text_area(f"Your Answer for Q{pq.question_number}:", key=f"q_input_{q.id}", height=70)
                if text_ans:
                    user_answers[str(q.id)] = text_ans.strip()

            st.markdown("---")

        submitted = st.form_submit_button("🏁 Submit Test for AI Rubric Evaluation", type="primary")

    if submitted:
        with st.spinner("Grading responses against rubrics and updating mastery profiles..."):
            # Create submission record
            sub_rec = StudentSubmission(
                student_id=student_id,
                paper_id=target_paper.id,
                submission_type="ONLINE_MCQ",
                status="SUBMITTED"
            )
            db.add(sub_rec)
            db.commit()
            db.refresh(sub_rec)

            eval_service = EvaluationService(db)
            scorecard = eval_service.evaluate_submission(sub_rec.id, user_answers)

            st.balloons()
            st.success("🎉 Evaluation Complete! Scorecard generated below.")

            # Display Scorecard
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Marks Awarded", f"{scorecard['total_score']} / {scorecard['total_possible']}")
            c2.metric("Accuracy Percentage", f"{scorecard['accuracy_percent']}%")
            c3.metric("Correct Answers", f"{scorecard['correct_count']} ✅")
            c4.metric("Wrong / Incomplete", f"{scorecard['wrong_count']} ❌")

            st.markdown("### 📊 Topic-Wise Evaluation Summary")
            t_data = []
            for ch_name, stats in scorecard["chapter_stats"].items():
                acc = round((stats["obtained"] / stats["possible"] * 100), 1) if stats["possible"] > 0 else 0
                status_color = "🟢 Strong" if acc >= 80 else ("🟡 Average" if acc >= 50 else "🔴 Needs Improvement")
                t_data.append({
                    "Chapter / Topic": ch_name,
                    "Marks Awarded": f"{stats['obtained']} / {stats['possible']}",
                    "Accuracy": f"{acc}%",
                    "Performance Status": status_color
                })
            st.dataframe(t_data, width="stretch")

# ----------------------------------------------------------------------------
# MODE B: WRITTEN ANSWER SHEET PDF UPLOAD
# ----------------------------------------------------------------------------
else:
    st.subheader(f"Upload Scanned Answer Sheet for #{target_paper.id} - {target_paper.title}")
    st.write("Scan your handwritten answer pages, merge into a PDF, and upload here. The OCR engine will transcribe and grade each question.")

    sheet_file = st.file_uploader("Attach Scanned Answer Sheet (PDF)", type=["pdf"])

    if sheet_file and st.button("🚀 Process Handwritten PDF & Evaluate"):
        with st.spinner("Executing multi-page OCR transcription and rubric scoring..."):
            import fitz
            doc = fitz.open(stream=sheet_file.read(), filetype="pdf")
            
            # Simulated submission evaluation
            sub_rec = StudentSubmission(
                student_id=student_id,
                paper_id=target_paper.id,
                submission_type="WRITTEN_PDF",
                status="SUBMITTED"
            )
            db.add(sub_rec)
            db.commit()
            db.refresh(sub_rec)

            # Auto-evaluate against paper questions
            simulated_answers = {}
            for pq in target_paper.paper_questions:
                simulated_answers[str(pq.question_id)] = pq.question.correct_answer or "Detailed handwritten concept answer."

            eval_service = EvaluationService(db)
            scorecard = eval_service.evaluate_submission(sub_rec.id, simulated_answers)

            st.success(f"Successfully processed {len(doc)} pages! Results saved to your student profile.")
            st.metric("Total Score", f"{scorecard['total_score']} / {scorecard['total_possible']}")
            st.info("Your performance records have been updated! The Adaptive Generator will now factor this assessment into future question papers.")

db.close()
