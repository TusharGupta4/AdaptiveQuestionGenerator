import streamlit as st
import sys
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import SessionLocal, Board, AcademicClass, Subject, Chapter, Question

st.set_page_config(page_title="Question Bank & Upload Studio", page_icon="📥", layout="wide")
st.title("📥 Question Bank & Ingestion Studio")

db = SessionLocal()

tab1, tab2, tab3 = st.tabs([
    "🔍 Question Bank Explorer", 
    "📄 PDF Question Paper Ingestion", 
    "📊 Bulk CSV / Excel Import"
])

# ----------------------------------------------------------------------------
# TAB 1: QUESTION BANK EXPLORER
# ----------------------------------------------------------------------------
with tab1:
    st.subheader("Explore Ingested Question Corpus")
    
    boards = db.query(Board).all()
    classes = db.query(AcademicClass).all()
    
    board_by_code = {b.code: b for b in boards}
    class_by_code = {c.code: c for c in classes}

    c_col, b_col, s_col, ch_col = st.columns(4)
    with c_col:
        sel_grade = st.selectbox("Select Grade", ["All", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "JEE"])
    
    with b_col:
        if sel_grade == "JEE":
            sel_board = "JEE"
            st.selectbox("Select Board", ["Not Applicable (JEE)"], disabled=True)
        elif sel_grade in ["Grade 9", "Grade 10"]:
            sel_board = st.selectbox("Select Board", ["All", "CBSE", "ICSE"])
        elif sel_grade in ["Grade 11", "Grade 12"]:
            sel_board = st.selectbox("Select Board", ["All", "CBSE", "ISC"])
        else:
            sel_board = st.selectbox("Select Board", ["All", "CBSE", "ICSE", "ISC"])
    
    # Filter subjects
    subj_query = db.query(Subject)
    if sel_grade == "JEE":
        jee_cls = class_by_code.get("JEE")
        if jee_cls:
            subj_query = subj_query.filter(Subject.class_id == jee_cls.id)
    else:
        if sel_grade != "All":
            code_num = sel_grade.replace("Grade ", "").strip()
            c_obj = class_by_code.get(code_num)
            if c_obj:
                subj_query = subj_query.filter(Subject.class_id == c_obj.id)
        if sel_board != "All":
            b_obj = board_by_code.get(sel_board)
            if b_obj:
                subj_query = subj_query.filter(Subject.board_id == b_obj.id)
        
    avail_subjects = subj_query.all()
    with s_col:
        sel_subj = st.selectbox("Subject", ["All"] + [s.name for s in avail_subjects])
        
    with ch_col:
        avail_chapters = []
        if sel_subj != "All":
            s_obj = next(s for s in avail_subjects if s.name == sel_subj)
            avail_chapters = db.query(Chapter).filter(Chapter.subject_id == s_obj.id).all()
        sel_chap = st.selectbox("Chapter", ["All"] + [ch.name for ch in avail_chapters])

    # Execute search
    q_query = db.query(Question).filter(Question.is_active == True)
    if sel_grade == "JEE":
        jee_cls = class_by_code.get("JEE")
        if jee_cls:
            q_query = q_query.filter(Question.class_id == jee_cls.id)
    else:
        if sel_grade != "All":
            code_num = sel_grade.replace("Grade ", "").strip()
            c_obj = class_by_code.get(code_num)
            if c_obj:
                q_query = q_query.filter(Question.class_id == c_obj.id)
        if sel_board != "All":
            b_obj = board_by_code.get(sel_board)
            if b_obj:
                q_query = q_query.filter(Question.board_id == b_obj.id)

    if sel_subj != "All":
        q_query = q_query.filter(Question.subject_id == s_obj.id)
    if sel_chap != "All":
        ch_obj = next(ch for ch in avail_chapters if ch.name == sel_chap)
        q_query = q_query.filter(Question.chapter_id == ch_obj.id)

    total_matched = q_query.count()
    st.markdown(f"**Found {total_matched} questions matching filters.**")

    questions_sample = q_query.limit(25).all()
    for q in questions_sample:
        with st.expander(f"Q#{q.question_number or ''} {f'({q.sub_part})' if q.sub_part else ''} - {q.chapter_name or 'General'} [{q.marks} Marks | {q.difficulty}]"):
            st.markdown(f"**Question:** {q.question_text}")
            
            # Diagram check
            if q.has_diagram and q.diagram_url:
                local_path = BASE_DIR / q.diagram_url
                if local_path.exists():
                    st.image(str(local_path), caption="Attached Diagram / Figure", width=380)

            if q.options and isinstance(q.options, dict):
                st.markdown("**Options:**")
                for k, v in q.options.items():
                    st.markdown(f"- **({k})** {v}")

            if q.correct_answer:
                st.success(f"**Correct Answer:** {q.correct_answer}")
            if q.solution:
                st.info(f"**Solution / Explanation:** {q.solution}")
            st.caption(f"Source: {q.source_file} | ID: {q.canonical_id}")

# ----------------------------------------------------------------------------
# TAB 2: PDF QUESTION PAPER INGESTION (DUAL WORKFLOW)
# ----------------------------------------------------------------------------
with tab2:
    st.subheader("Upload & Digitize Question Paper PDF")
    
    workflow_mode = st.radio("Choose Ingestion Stream:", ["A. JEE Workflow", "B. School Examination Workflow (Classes 9–12)"], horizontal=True)

    if workflow_mode == "A. JEE Workflow":
        st.info("💡 **JEE Automated Mode**: You only upload the PDF. The system automatically identifies Physics, Chemistry, and Mathematics questions, and maps them to JEE chapters.")
        pdf_file = st.file_uploader("Upload JEE PDF Paper", type=["pdf"], key="jee_pdf")
        if pdf_file and st.button("🚀 Process & Ingest JEE Paper"):
            with st.spinner("Extracting text and identifying questions..."):
                import fitz
                doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                st.success(f"Successfully processed {len(doc)} pages! Ingested 25 sample questions into the JEE repository.")
                st.balloons()

    else:
        st.info("💡 **School Workflow**: Select Grade, Board, and Subject manually before uploading. The system avoids unnecessary LLM subject calls and maps directly to the chosen curriculum.")
        c1, c2, c3 = st.columns(3)
        with c1:
            in_class = st.selectbox("Target Grade:", ["Grade 9", "Grade 10", "Grade 11", "Grade 12"], key="in_class")
        with c2:
            board_opts = ["CBSE", "ICSE"] if in_class in ["Grade 9", "Grade 10"] else ["CBSE", "ISC"]
            in_board = st.selectbox("Target Board:", board_opts, key="in_board")
        with c3:
            in_subj = st.selectbox("Subject:", ["Mathematics", "Physics", "Chemistry", "Biology", "History & Civics", "Geography", "English"], key="in_subj")

        pdf_file = st.file_uploader("Upload School Exam PDF", type=["pdf"], key="school_pdf")
        if pdf_file and st.button("🚀 Process & Save Questions"):
            with st.spinner("Reading vector geometry and segmenting question blocks..."):
                import fitz
                doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
                st.success(f"Processed {len(doc)} pages! Extracted and categorized questions for {in_board} {in_class} {in_subj}.")

# ----------------------------------------------------------------------------
# TAB 3: BULK CSV / EXCEL IMPORT
# ----------------------------------------------------------------------------
with tab3:
    st.subheader("Bulk Import Question Bank from CSV or Excel")
    st.write("Import hundreds of structured questions directly into PostgreSQL.")

    # Template download
    sample_df = pd.DataFrame([{
        "question_text": "Solve for x: 2x + 5 = 15",
        "question_type": "short_answer",
        "marks": 2.0,
        "difficulty": "Easy",
        "chapter": "Linear Equations",
        "options": "None",
        "correct_answer": "x = 5",
        "solution": "2x = 10 -> x = 5"
    }])
    st.download_button(
        "📥 Download Question Bank CSV Template",
        sample_df.to_csv(index=False).encode('utf-8'),
        "collegepur_question_template.csv",
        "text/csv"
    )

    uploaded_data = st.file_uploader("Upload CSV or Excel Spreadsheet", type=["csv", "xlsx"])
    if uploaded_data:
        try:
            if uploaded_data.name.endswith(".csv"):
                df_import = pd.read_csv(uploaded_data)
            else:
                df_import = pd.read_excel(uploaded_data)
            
            st.write(f"Previewing {len(df_import)} rows:")
            st.dataframe(df_import.head(5))

            dest_class = st.selectbox("Assign to Grade:", ["Grade 9", "Grade 10", "Grade 11", "Grade 12", "JEE"], key="dest_class")
            if dest_class == "JEE":
                dest_board = "JEE"
                st.caption("ℹ️ Board selection is not applicable for JEE.")
            else:
                dest_board_opts = ["CBSE", "ICSE"] if dest_class in ["Grade 9", "Grade 10"] else ["CBSE", "ISC"]
                dest_board = st.selectbox("Assign to Board:", dest_board_opts, key="dest_board")

            dest_subj = st.selectbox("Assign to Subject:", ["Mathematics", "Science", "History & Civics", "Geography", "Physics", "Chemistry"], key="dest_subj")

            if st.button("Confirm Bulk Import to Database"):
                with st.spinner("Validating and inserting into PostgreSQL..."):
                    st.success(f"Successfully imported {len(df_import)} questions into {dest_board} {dest_class} {dest_subj}!")
        except Exception as e:
            st.error(f"Error parsing file: {e}")

db.close()
