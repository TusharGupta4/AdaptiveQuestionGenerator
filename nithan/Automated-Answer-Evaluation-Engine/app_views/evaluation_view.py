from typing import Dict

import streamlit as st

from src import feedback_llm, ocr_engine, rubric_evaluator


def _question_reference(question: Dict) -> str:
    return (
        question.get('reference_answer')
        or question.get('reference_ans')
        or question.get('reference')
        or ''
    )


def _question_keywords(question) -> str:
    if isinstance(question, dict):
        return question.get('keywords') or question.get('key_words') or ''
    return question or ''


def render_evaluation(qid: str, question: Dict, student_text: str,
                      eval_result: Dict, selected_class=None,
                      diagrams=None, source_expanded=False,
                      source_label="View mapped answer text") -> None:
    question = question or st.session_state.get('selected_question') or {}
    selected_class = (
        selected_class
        or st.session_state.get('selected_class')
        or st.session_state.get('sb_class')
        or eval_result.get('selected_class')
    )
    has_reference = eval_result.get('has_reference', True)
    max_marks = eval_result.get('max_marks', question.get('max_marks', 5.0))
    scoring_mode = eval_result.get('scoring_mode', 'rubric')

    if has_reference:
        title = f"{qid} - {eval_result['awarded_marks']:.2f}/{max_marks:.2f} marks"
    else:
        title = f"{qid} - Zero-Shot LLM (max {max_marks:.2f} marks)"

    with st.expander(title, expanded=True):
        question_text = question.get('question_text')
        if question_text:
            st.caption(f"Question: {question_text}")
        subject_type = eval_result.get('subject_type', 'humanities')
        st.caption(
            f"Scoring mode: {scoring_mode} | Subject type: {subject_type} | "
            f"Max marks: {max_marks:.2f}"
        )
        grade_label = eval_result.get('grade_profile_label')
        if grade_label:
            st.caption(
                f"Grade profile: {grade_label} "
                f"({eval_result.get('grade_band', selected_class or '')}) | "
                f"Keyword threshold: {eval_result.get('keyword_threshold', 65.0):.0f}% | "
                f"Min words after tolerance: "
                f"{eval_result.get('effective_min_words', 0):.0f}"
            )

        weights = eval_result.get('weights_used') or eval_result.get('weight_matrix') or {}
        keyword_threshold = eval_result.get('keyword_threshold', 65.0)

        if has_reference:
            st.markdown("**Metric Breakdown:**")
            st.progress(min((eval_result.get('semantic_score') or 0) / 100, 1.0))
            st.caption(
                f"Semantic Match: {eval_result.get('semantic_score', 0):.1f}% "
                f"({weights.get('semantic', 0.40) * 100:.0f}% weight)"
            )

            st.progress(min((eval_result.get('fuzzy_keyword_score') or 0) / 100, 1.0))
            st.caption(
                f"Fuzzy Keyword Match: {eval_result.get('fuzzy_keyword_score', 0):.1f}% "
                f"({weights.get('fuzzy_keyword', 0.30) * 100:.0f}% weight, "
                f">={keyword_threshold:.0f}% threshold)"
            )

            if eval_result.get('equation_score') is not None:
                st.progress(min((eval_result.get('equation_score') or 0) / 100, 1.0))
                st.caption(
                    f"Equation Accuracy / SymPy: "
                    f"{eval_result.get('equation_score', 0):.1f}% "
                    f"({weights.get('equation_accuracy', 0) * 100:.0f}% weight)"
                )

            if eval_result.get('diagram_label_score') is not None:
                st.progress(min((eval_result.get('diagram_label_score') or 0) / 100, 1.0))
                st.caption(
                    f"Diagram Label Match: "
                    f"{eval_result.get('diagram_label_score', 0):.1f}% "
                    f"({weights.get('diagram_label', 0) * 100:.0f}% weight)"
                )
                missing_labels = eval_result.get('diagram_labels_missing') or []
                if missing_labels:
                    st.caption(
                        "Missing diagram labels: " + ", ".join(missing_labels)
                    )
        else:
            st.warning(
                "No reference answer or keywords were found for this question. "
                "Semantic and keyword matching were skipped."
            )
            st.info(
                "Zero-Shot LLM Mode is active: the answer is assessed against "
                f"general domain knowledge out of {max_marks:.2f} marks."
            )
            zero_shot_subscores = eval_result.get('sub_scores') or {}
            diagnostic_rows = (
                ('word_count', 'Word Count Score'),
                ('ocr_quality', 'OCR Quality'),
                ('diagram_label', 'Diagram Label Match'),
                ('equation_accuracy', 'Equation Accuracy / SymPy'),
            )
            visible_diagnostics = [
                (name, label)
                for name, label in diagnostic_rows
                if zero_shot_subscores.get(name) is not None
            ]
            if visible_diagnostics:
                st.markdown("**Zero-Shot Diagnostic Sub-Scores:**")
                for name, label in visible_diagnostics:
                    value = zero_shot_subscores.get(name) or 0
                    st.progress(min(value / 100, 1.0))
                    st.caption(f"{label}: {value:.1f}%")

        col_m1, col_m2, col_m3 = st.columns(3)
        with col_m1:
            st.metric("Word Count", eval_result.get('word_count', 0))
        with col_m2:
            st.metric("Word Count Score", f"{eval_result.get('word_count_score', 0):.1f}%")
        with col_m3:
            st.metric("OCR Quality", f"{eval_result.get('ocr_quality_score', 0):.1f}%")

        keyword_list = rubric_evaluator.normalize_keywords(_question_keywords(question))
        missing_keywords = []
        recognized = []
        formal_terms = bool(eval_result.get('formal_term_validation'))
        if has_reference and keyword_list:
            missing_keywords = [
                keyword for keyword in keyword_list
                if not rubric_evaluator.fuzzy_match_keyword(
                    keyword,
                    student_text,
                    keyword_threshold,
                    formal=formal_terms,
                )
            ]
            recognized = [
                keyword for keyword in keyword_list
                if rubric_evaluator.fuzzy_match_keyword(
                    keyword,
                    student_text,
                    keyword_threshold,
                    formal=formal_terms,
                )
            ][:3]

        feedback_result = {}
        feedback_error = None
        try:
            feedback_result = feedback_llm.generate_feedback_result(
                student_score=eval_result.get('score'),
                missing_keywords=missing_keywords,
                reference_answer=_question_reference(question),
                student_answer=student_text,
                awarded_marks=eval_result.get('awarded_marks'),
                max_marks=max_marks,
                recognized_concepts=recognized,
                has_reference=has_reference,
                scoring_mode=scoring_mode,
                question_text=question.get('question_text', ''),
                selected_class=selected_class or eval_result.get('selected_class'),
            )
        except Exception as error:
            feedback_error = str(error)

        if has_reference:
            awarded_marks = eval_result.get('awarded_marks')
            if awarded_marks is not None:
                st.markdown(
                    f"### Marks Awarded: **{awarded_marks:.2f}** / "
                    f"Max Marks **{max_marks:.2f}**"
                )
        else:
            estimated_marks = feedback_result.get('estimated_marks')
            if estimated_marks is not None:
                st.markdown(
                    f"### Marks Awarded: **{estimated_marks:.2f}** / "
                    f"Max Marks **{max_marks:.2f}**"
                )
                st.caption("Marks estimated by the zero-shot LLM assessment.")
            else:
                st.markdown(
                    f"### Marks Awarded: **Unavailable** / "
                    f"Max Marks **{max_marks:.2f}**"
                )
                st.caption(
                    "The zero-shot LLM did not return a valid mark estimate; "
                    "the feedback below uses the deterministic fallback."
                )

        if feedback_error:
            st.error(f"Feedback error: {feedback_error}")
        elif feedback_result.get('qualitative_feedback'):
            st.markdown("**Qualitative LLM Feedback:**")
            st.info(feedback_result['qualitative_feedback'])

        with st.expander(source_label, expanded=source_expanded):
            st.text(student_text)
            detected_diagrams = diagrams or eval_result.get('diagrams') or []
            if detected_diagrams:
                st.markdown("**Detected Diagrams**")
                for index, diagram in enumerate(detected_diagrams, start=1):
                    st.markdown(
                        f"**{diagram.get('figure_id') or f'Figure {index}'}**"
                    )
                    if diagram.get('description'):
                        st.caption(diagram['description'])
                    labels = ocr_engine.normalize_label_list(diagram.get('labels'))
                    if labels:
                        st.caption("Labels: " + ", ".join(labels))
                    if diagram.get('spatial_arrangement'):
                        st.caption(
                            "Layout: " + str(diagram['spatial_arrangement'])
                        )
                    relationships = ocr_engine.normalize_label_list(
                        diagram.get('relationships')
                    )
                    if relationships:
                        st.caption(
                            "Relationships: " + ", ".join(relationships)
                        )

