import os
import tempfile
from typing import Dict, List, Optional

import streamlit as st

from app_views.evaluation_view import render_evaluation
from src import data_loader, ocr_engine, pdf_processor, rubric_evaluator

SAMPLE_DIR = data_loader.DEFAULT_SAMPLE_DIR
ALL_QUESTIONS = data_loader.ALL_QUESTIONS


def format_question_option(question_no: str, question: Dict, limit: int = 100) -> str:
    """Formats question numbers and text previews for selectbox dropdowns."""
    return data_loader.format_question_option(
        question_no, question.get('question_text', ''), limit=limit
    )


def _as_question_map(questions) -> Dict[str, Dict]:
    """Converts a question list or dict into a standard key-indexed map."""
    if isinstance(questions, dict):
        return dict(questions)
    result = {}
    for question in questions or []:
        qid = question.get('question_no') or question.get('question_id')
        if qid:
            result[qid] = question
    return result


def build_question_text_map(
    page_texts,
    questions,
    mode: str,
    selected_qid: Optional[str] = None,
    question_blocks: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    """Maps continuous document transcription text to target question answer blocks."""
    question_map = _as_question_map(questions)
    page_blocks = [
        str(text).strip()
        for text in (page_texts if isinstance(page_texts, list) else [page_texts])
        if str(text).strip()
    ]
    combined_text = ocr_engine.assemble_page_texts(page_blocks)
    if not combined_text:
        return {}

    expected_ids = list(question_map.keys())
    if question_blocks is None:
        question_blocks = ocr_engine.extract_full_document_questions(
            combined_text, expected_ids, use_groq=False
        )

    normalized_blocks = rubric_evaluator.normalize_block_map(question_blocks)

    if mode != ALL_QUESTIONS and selected_qid in question_map:
        block = normalized_blocks.get(selected_qid, '').strip()
        return {selected_qid: block or combined_text}

    if not expected_ids:
        return {}

    matches = rubric_evaluator.match_questions_to_blocks(
        list(question_map.values()), normalized_blocks
    )

    result = {}
    for qid in expected_ids:
        match = matches.get(qid, {})
        text = (match.get('text') or '').strip()
        result[qid] = text or combined_text
    return result


def render_active_question_context(
    class_name: str,
    subject: str,
    paper: str,
    questions: List[Dict],
    selected_question: Optional[Dict],
) -> None:
    """Displays hierarchy context and target question metadata cards."""
    st.subheader("Active Question Context")
    hierarchy = f"{class_name} -> {subject} -> {paper}"

    if selected_question:
        max_marks = selected_question.get('max_marks', 5.0)
        scoring_mode = selected_question.get('scoring_mode', 'rubric')
        with st.container(border=True):
            st.markdown(f"**{hierarchy} -> {selected_question['question_no']}**")
            st.markdown(selected_question.get('question_text') or 'No question text available.')
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Max Marks", f"{max_marks:g}")
            with col_b:
                st.metric(
                    "Scoring Mode",
                    "Zero-Shot LLM" if scoring_mode == 'zero_shot_llm' else "Rubric",
                )
        return

    with st.container(border=True):
        st.markdown(f"**All Questions - {hierarchy}**")
        for question in questions:
            max_marks = question.get('max_marks', 5.0)
            question_text = question.get('question_text') or 'No question text available.'
            st.markdown(f"- **{question['question_no']}** ({max_marks:g} marks): {question_text}")


def render_question_bank_mode() -> None:
    """Main view renderer for Question Bank mode."""
    classes = data_loader.get_available_classes(SAMPLE_DIR)
    if not classes:
        st.error("No Class/Grade folders were found under sample_data/.")
        return

    with st.sidebar:
        st.header("Evaluation Target")
        sb_class = st.selectbox("Class / Grade", classes, key="sb_class")
        subjects = data_loader.get_available_subjects(sb_class, SAMPLE_DIR)
        if not subjects:
            st.error(f"No subject folders found in '{sb_class}'.")
            return

        sb_subject = st.selectbox("Subject", subjects, key=f"sb_subject::{sb_class}")
        papers = data_loader.get_available_papers(sb_class, sb_subject, SAMPLE_DIR)
        if not papers:
            st.error(f"No CSV papers found for {sb_class} -> {sb_subject}.")
            return

        sb_paper = st.selectbox(
            "Question Paper / Assignment", papers, key=f"sb_paper::{sb_class}::{sb_subject}"
        )
        questions = data_loader.load_paper_questions(sb_class, sb_subject, sb_paper, SAMPLE_DIR)
        if not questions:
            st.error(f"No questions loaded from {sb_class}/{sb_subject}/{sb_paper}.csv.")
            return

        options = data_loader.get_question_options(sb_class, sb_subject, sb_paper, SAMPLE_DIR)
        sb_question = st.selectbox(
            "Question Mapping Mode",
            options,
            key=f"sb_question::{sb_class}::{sb_subject}::{sb_paper}",
        )
        mode_choice = sb_question

        if mode_choice == ALL_QUESTIONS:
            selected_qid, selected_question, target_label = None, None, ALL_QUESTIONS
        else:
            selected_index = options.index(mode_choice) - 1
            selected_question = questions[selected_index]
            selected_qid = selected_question['question_no']
            target_label = mode_choice

        st.markdown("---")
        st.caption(f"{len(questions)} question(s) available in this paper.")

    st.info(f"Target Question Selected: {sb_class} -> {sb_subject} -> {sb_paper} -> {target_label}")
    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Upload & Preview")
        uploaded_file = st.file_uploader("Upload PDF or Image", type=['pdf', 'jpg', 'jpeg', 'png'])
        file_path = None

        if uploaded_file is not None:
            suffix = os.path.splitext(uploaded_file.name)[1]
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(uploaded_file.getvalue())
                file_path = tmp.name
            st.success(f"Uploaded: {uploaded_file.name}")

            try:
                preview_images = pdf_processor.process_file(file_path, dpi=150)
                for idx, img in enumerate(preview_images):
                    st.image(img, caption=f"Page {idx + 1}", width='stretch')
            except Exception as error:
                st.error(f"Error loading preview: {error}")

        evaluate_btn = st.button("Run Evaluation", type="primary", width='stretch')

    with col2:
        st.header("OCR & Results")
        render_active_question_context(sb_class, sb_subject, sb_paper, questions, selected_question)

        if not evaluate_btn or not file_path:
            if evaluate_btn and not file_path:
                st.error("Please upload a PDF or image first.")
            else:
                st.info("Upload a file and click 'Run Evaluation' to start.")
            return

        with st.spinner("Processing document through multi-page OCR engine..."):
            try:
                proc_images = pdf_processor.process_file(file_path, dpi=300)
            except Exception as error:
                st.error(f"Error loading pages: {error}")
                return

            paper_subject_type = next(
                (q.get('subject_type') for q in questions if q.get('subject_type')), ''
            )

            # Direct backend pipeline execution
            doc_result = ocr_engine.extract_document_from_pages(
                proc_images,
                use_groq=True,
                subject_type=paper_subject_type,
                subject=sb_subject,
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
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.metric("Confidence", f"{confidence:.2f}%")
                    with col_b:
                        is_bad = res.get('is_illegible', confidence < 40)
                        st.metric("Status", "Low Quality" if is_bad else "Legible")
                    st.text_area("Page Text", text, height=120, key=f"page_text_{idx}")

            combined_text = doc_result['full_text']
            expected_ids = [q['question_no'] for q in questions]

            question_blocks = ocr_engine.extract_full_document_questions(
                combined_text, expected_ids, use_groq=True
            )
            question_map = build_question_text_map(
                doc_result['page_texts'],
                questions,
                mode_choice,
                selected_qid,
                question_blocks=question_blocks,
            )

            st.subheader("Evaluation Results")
            targeted_ids = [selected_qid] if selected_qid else expected_ids
            questions_by_id = {q['question_no']: q for q in questions}

            for qid in targeted_ids:
                question = questions_by_id.get(qid, {})
                student_text = question_map.get(qid, '')
                eval_result = rubric_evaluator.evaluate_question(
                    student_text,
                    question,
                    min_words=10,
                    diagrams=doc_result.get('diagrams', []),
                    selected_class=sb_class,
                )
                render_evaluation(
                    qid,
                    question,
                    student_text,
                    eval_result,
                    selected_class=sb_class,
                    diagrams=doc_result.get('diagrams', []),
                )
