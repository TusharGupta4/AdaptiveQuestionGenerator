import os
import tempfile
from typing import Dict, List, Optional

import streamlit as st

from app_views.evaluation_view import render_evaluation
from src import data_loader, ocr_engine, pdf_processor, rubric_evaluator

CUSTOM_CLASS_OPTIONS = [f'Class {n}' for n in range(6, 13)]
CUSTOM_SUBJECT_OPTIONS = [
    'Geography', 'Biology', 'Economics', 'Mathematics', 'Physics',
    'Chemistry', 'History', 'Political Science', 'English',
    'Environmental Science', 'Other',
]


def format_question_option(question_no: str, question_text: str, limit: int = 100) -> str:
    """Formats question option dropdown labels."""
    return data_loader.format_question_option(question_no, question_text, limit=limit)


def _stage_uploaded_file(uploaded_file) -> str:
    """Persists uploaded Streamlit file bytes to a temporary disk path."""
    suffix = os.path.splitext(getattr(uploaded_file, 'name', ''))[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def _load_custom_question_csv(uploaded_file, subject: str) -> List[Dict]:
    """Loads ad-hoc CSV questions using data_loader."""
    path = _stage_uploaded_file(uploaded_file)
    try:
        return data_loader.load_questions_csv(path, subject=subject, paper='custom_upload')
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _manual_custom_question(
    question_text: str, max_marks: float, selected_class: str, subject: str
) -> Dict:
    """Constructs a standard question dictionary from manual user text input."""
    return {
        'question_no': 'Custom Q1',
        'question_id': 'Custom Q1',
        'question_number': 'Custom Q1',
        'question_text': (question_text or '').strip(),
        'max_marks': max_marks,
        'subject_type': rubric_evaluator.resolve_subject_type(subject=subject),
        'required_diagram_labels': '',
        'required_diagram_label_list': [],
        'class_name': selected_class,
        'class': selected_class,
        'subject': subject,
        'paper': 'custom_upload',
    }


def render_custom_evaluation_mode() -> None:
    """Main view renderer for Custom Evaluation mode."""
    st.header("Custom Evaluation (Ad-Hoc Testing)")
    st.caption("Evaluate a custom question and handwritten sheet directly.")

    selected_question = None
    control_col, answer_col = st.columns([1, 1])

    with control_col:
        st.subheader("1. Evaluation Target")
        target_col, subject_col = st.columns(2)
        with target_col:
            selected_class = st.selectbox("Class / Grade", CUSTOM_CLASS_OPTIONS, key='custom_class')
        with subject_col:
            subject = st.selectbox("Subject", CUSTOM_SUBJECT_OPTIONS, key='custom_subject')

        question_source = st.radio(
            "Question Input",
            ("Type Question Manually", "Upload Custom Question CSV"),
            key='custom_question_source',
        )

        if question_source == "Type Question Manually":
            question_text = st.text_area(
                "Question Text",
                height=140,
                key='custom_question_text',
                placeholder="e.g. What do you mean by Geoid? Discuss evidence of Earth's sphericity.",
            )
            max_marks = st.number_input(
                "Max Marks", min_value=1.0, max_value=100.0, value=10.0, step=0.5, key='custom_max_marks'
            )
            selected_question = _manual_custom_question(
                question_text, max_marks, selected_class, subject
            )
        else:
            question_csv = st.file_uploader(
                "Upload Custom Question CSV", type=['csv'], key='custom_question_csv'
            )
            if question_csv is not None:
                try:
                    custom_questions = _load_custom_question_csv(question_csv, subject)
                except Exception as error:
                    custom_questions = []
                    st.error(f"Could not parse question CSV: {error}")

                if custom_questions:
                    selected_index = st.selectbox(
                        "Select Custom Question",
                        options=list(range(len(custom_questions))),
                        format_func=lambda i: format_question_option(
                            custom_questions[i]['question_no'],
                            custom_questions[i].get('question_text', ''),
                        ),
                        key='custom_csv_question_select',
                    )
                    selected_question = dict(custom_questions[selected_index])
                    selected_question['class_name'] = selected_class
                    selected_question['class'] = selected_class
                    selected_question['subject'] = subject
                    selected_question['paper'] = 'custom_upload'
                    if not selected_question.get('subject_type'):
                        selected_question['subject_type'] = rubric_evaluator.resolve_subject_type(
                            subject=subject
                        )
                else:
                    st.error("No valid questions found in uploaded CSV.")

    with answer_col:
        st.subheader("2. Handwritten Sheet Upload")
        uploaded_file = st.file_uploader(
            "Upload PDF or Image", type=['pdf', 'jpg', 'jpeg', 'png'], key='custom_answer_file'
        )
        file_path = None
        if uploaded_file is not None:
            file_path = _stage_uploaded_file(uploaded_file)
            st.success(f"Uploaded: {uploaded_file.name}")
            try:
                preview_images = pdf_processor.process_file(file_path, dpi=150)
                for index, image in enumerate(preview_images):
                    st.image(image, caption=f"Page {index + 1}", width='stretch')
            except Exception as error:
                st.error(f"Error loading preview: {error}")

        evaluate_btn = st.button("Evaluate Custom Answer", type="primary", width='stretch')

    if not evaluate_btn or not file_path or not selected_question:
        if evaluate_btn and not selected_question:
            st.error("Please enter or select a custom question first.")
        elif evaluate_btn and not file_path:
            st.error("Please upload a PDF or image first.")
        return

    question = dict(selected_question)
    question['question_text'] = question.get('question_text', '').strip()

    try:
        with st.spinner("Extracting handwritten sheet through multi-page OCR..."):
            proc_images = pdf_processor.process_file(file_path, dpi=300)
            doc_result = ocr_engine.extract_document_from_pages(
                proc_images,
                use_groq=True,
                subject_type=question.get('subject_type', ''),
                subject=subject,
            )

        st.subheader("OCR Engine Status")
        for page in doc_result.get('page_results', []):
            idx = page['page_number']
            text = page['text']
            res = page.get('result', {})
            confidence = res.get('average_confidence', res.get('confidence', 0.0))
            engine = res.get('engine', res.get('method', 'Groq VLM'))

            with st.expander(f"Page {idx} OCR Results", expanded=(idx == 1)):
                st.info(f"Active Engine: {engine}")
                st.metric("Confidence", f"{confidence:.2f}%")
                st.text_area("Page Text", text, height=120, key=f"custom_page_text_{idx}")

        combined_text = doc_result['full_text']
        if not combined_text.strip():
            st.warning("No handwritten text extracted.")
            return

        eval_result = rubric_evaluator.evaluate_question(
            combined_text,
            question,
            min_words=10,
            diagrams=doc_result.get('diagrams', []),
            selected_class=selected_class,
        )

        st.subheader("Custom Evaluation Results")
        qid = question.get('question_no') or 'Custom Q1'
        render_evaluation(
            qid,
            question,
            combined_text,
            eval_result,
            selected_class=selected_class,
            diagrams=doc_result.get('diagrams', []),
            source_expanded=True,
            source_label="View extracted answer text",
        )
    finally:
        if file_path:
            try:
                os.unlink(file_path)
            except OSError:
                pass
