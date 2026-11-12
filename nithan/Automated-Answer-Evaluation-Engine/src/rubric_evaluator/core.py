from typing import Dict, List

try:
    from .. import config as grade_config
except ImportError:
    import config as grade_config

from .payload_mappers import (
    build_grade_fields,
    build_reference_result,
    build_subject_fields,
    build_zero_shot_result,
    resolve_question_context,
)
from .scoring import (
    SYMPY_AVAILABLE,
    _coerce_marks,
    _normalize_keywords,
    compute_dimension_scores,
    compute_reference_scores,
    compute_weighted_score,
    compute_word_and_ocr_scores,
    get_subject_weights,
    resolve_subject_type,
)


def evaluate_answer(student_text: str, reference_answer: str,
                   keywords: List[str] = None,
                   max_marks: float = 5.0,
                   min_words: int = 10,
                   default_max_marks: float = 5.0,
                   subject_type: str = None,
                   subject: str = None,
                   selected_class=None,
                   required_diagram_labels=None,
                   diagrams=None) -> Dict:
    """
    Multi-Dimensional Rubric Engine with subject- and grade-aware weights.

    The grade profile selected through ``selected_class`` controls the fuzzy
    keyword threshold, word-count tolerance, formal technical-term validation,
    and semantic/keyword weight priorities. Subject profiles then determine
    whether equation accuracy or diagram-label matching is also weighted.

    When no reference answer/keywords are available for a question, semantic
    similarity and fuzzy keyword matching are skipped and the result is marked
    for zero-shot LLM scoring instead.
    """
    reference_text = reference_answer.strip() if isinstance(reference_answer, str) else ''
    keyword_list = _normalize_keywords(keywords)
    has_reference = bool(reference_text or keyword_list)

    resolved_max_marks = _coerce_marks(max_marks, _coerce_marks(default_max_marks, 5.0))
    fallback_max_marks = _coerce_marks(default_max_marks, 5.0)
    grade_profile = grade_config.resolve_grade_profile(selected_class)
    keyword_threshold = (
        grade_profile['keyword_threshold']
        if grade_profile else grade_config.DEFAULT_KEYWORD_THRESHOLD
    )
    word_count_tolerance = (
        grade_profile['word_count_tolerance']
        if grade_profile else grade_config.DEFAULT_WORD_COUNT_TOLERANCE
    )
    word_count_penalty_scale = (
        grade_profile['word_count_penalty_scale']
        if grade_profile else grade_config.DEFAULT_WORD_COUNT_PENALTY_SCALE
    )
    formal_term_validation = bool(
        grade_profile and grade_profile.get('formal_term_validation')
    )
    resolved_subject_type = resolve_subject_type(
        subject_type,
        subject,
        required_diagram_labels,
    )
    weights = get_subject_weights(
        subject_type,
        subject,
        required_diagram_labels,
        selected_class=selected_class,
    )

    # c) Grade-aware Word Count Penalty - independent of reference data
    score_values = compute_word_and_ocr_scores(
        student_text,
        min_words,
        word_count_tolerance,
        word_count_penalty_scale,
    )
    word_count = score_values['word_count']
    effective_min_words = score_values['effective_min_words']
    word_count_score = score_values['word_count_score']
    word_count_penalty_applied = score_values['word_count_penalty_applied']
    garbled_ratio = score_values['garbled_ratio']
    ocr_quality_score = score_values['ocr_quality_score']
    ocr_penalty_applied = score_values['ocr_penalty_applied']

    equation_score, equation_details, diagram_score, diagram_details = compute_dimension_scores(
        resolved_subject_type,
        reference_text,
        student_text,
        required_diagram_labels,
        diagrams,
        keyword_threshold,
        formal_term_validation,
    )

    subject_fields = build_subject_fields(
        resolved_subject_type,
        weights,
        equation_score,
        equation_details,
        diagram_score,
        diagram_details,
        SYMPY_AVAILABLE,
    )
    grade_fields = build_grade_fields(
        selected_class,
        grade_profile,
        keyword_threshold,
        formal_term_validation,
        word_count_tolerance,
        effective_min_words,
        word_count_penalty_scale,
    )

    if not has_reference:
        zero_shot_sub_scores = {
            'semantic': None,
            'fuzzy_keyword': None,
            'word_count': word_count_score,
            'ocr_quality': ocr_quality_score,
        }
        if equation_score is not None or resolved_subject_type == 'stem':
            zero_shot_sub_scores['equation_accuracy'] = equation_score
        if diagram_score is not None or resolved_subject_type == 'diagram_based':
            zero_shot_sub_scores['diagram_label'] = diagram_score

        return build_zero_shot_result(
            fallback_max_marks,
            word_count,
            word_count_score,
            word_count_penalty_applied,
            garbled_ratio,
            ocr_quality_score,
            ocr_penalty_applied,
            zero_shot_sub_scores,
            subject_fields,
            grade_fields,
        )

    emb_sim, semantic_score, kw_ratio, fuzzy_keyword_score, sub_scores = compute_reference_scores(
        student_text,
        reference_text,
        keyword_list,
        keyword_threshold,
        formal_term_validation,
        equation_score,
        resolved_subject_type,
        diagram_score,
        word_count_score,
        ocr_quality_score,
    )

    weighted_score, effective_weights = compute_weighted_score(
        sub_scores,
        weights,
    )

    # Awarded marks out of max_marks
    awarded_marks = (weighted_score / 100.0) * resolved_max_marks
    awarded_marks = max(0.0, min(resolved_max_marks, awarded_marks))

    return build_reference_result(
        weighted_score,
        awarded_marks,
        resolved_max_marks,
        emb_sim,
        semantic_score,
        kw_ratio,
        fuzzy_keyword_score,
        word_count,
        word_count_score,
        word_count_penalty_applied,
        garbled_ratio,
        ocr_quality_score,
        ocr_penalty_applied,
        sub_scores,
        effective_weights,
        subject_fields,
        grade_fields,
    )


def evaluate_question(student_text: str, question: Dict,
                      min_words: int = 10,
                      default_max_marks: float = 5.0,
                      diagrams=None,
                      selected_class=None) -> Dict:
    """
    Evaluate the student's response against one specific question record.

    All reference data (answer key, keywords, max marks, subject_type and
    required_diagram_labels) is read from the supplied question, which prevents
    a response from being compared against an unrelated question paper. The
    selected class activates the matching grade strictness profile.
    """
    question = question or {}
    context = resolve_question_context(
        question,
        diagrams,
        selected_class,
        default_max_marks,
    )

    from . import evaluate_answer as current_evaluate_answer

    result = current_evaluate_answer(
        student_text,
        context['reference'],
        keywords=context['keywords'],
        max_marks=context['resolved_max_marks'],
        min_words=min_words,
        default_max_marks=default_max_marks,
        subject_type=context['subject_type'],
        subject=question.get('subject') or question.get('subject_name') or '',
        selected_class=context['selected_class'],
        required_diagram_labels=context['required_diagram_labels'],
        diagrams=context['diagrams'],
    )
    if not result.get('has_reference', True):
        # Zero-shot scoring must still respect the selected question's marks.
        result['max_marks'] = context['resolved_max_marks']
    result['question_id'] = (
        question.get('question_id') or question.get('id')
        or question.get('question_no') or ''
    )
    result['question_text'] = question.get('question_text') or question.get('question') or ''
    return result
