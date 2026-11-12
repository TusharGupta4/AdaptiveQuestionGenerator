from .core import evaluate_answer, evaluate_question
from .feature_extractors import (
    RAPIDFUZZ_AVAILABLE,
    _dedupe_labels,
    _diagram_labels_from_payload,
    _normalize_equation,
    _normalize_label_list,
    _strip_math_delimiters,
    cosine_similarity,
    extract_equations,
    fuzzy_match_keyword,
    get_embeddings,
    keyword_match_ratio,
)
from .payload_mappers import (
    _coerce_block_map,
    compute_cosine_similarity,
    find_best_semantic_block,
    match_questions_to_blocks,
)
from .scoring import (
    DEFAULT_WEIGHTS,
    SUBJECT_WEIGHTS,
    SYMPY_AVAILABLE,
    _apply_grade_profile_to_weights,
    _coerce_marks,
    _equation_accuracy,
    _equation_similarity,
    _normalize_keywords,
    _sympy_equivalent,
    _sympy_expression,
    compute_garbled_ratio,
    get_subject_weights,
    resolve_subject_type,
)

normalize_keywords = _normalize_keywords
rubric_evaluate = evaluate_answer
score_answer = evaluate_answer
evaluate_for_question = evaluate_question
semantic_match_block = find_best_semantic_block
match_answers_to_questions = match_questions_to_blocks
route_questions_to_blocks = match_questions_to_blocks
normalize_block_map = _coerce_block_map
normalize_diagram_labels = _normalize_label_list
diagram_labels_from_payload = _diagram_labels_from_payload
extract_formulas = extract_equations
get_weights = get_subject_weights
resolve_subject = resolve_subject_type

__all__ = [
    'evaluate_answer',
    'evaluate_question',
    'get_embeddings',
    'fuzzy_match_keyword',
    'cosine_similarity',
    'keyword_match_ratio',
    'compute_garbled_ratio',
    'resolve_subject_type',
    'get_subject_weights',
    'find_best_semantic_block',
    'match_questions_to_blocks',
    'extract_equations',
    'compute_cosine_similarity',
    'normalize_keywords',
    'rubric_evaluate',
    'score_answer',
    'evaluate_for_question',
    'semantic_match_block',
    'match_answers_to_questions',
    'route_questions_to_blocks',
    'normalize_block_map',
    'normalize_diagram_labels',
    'diagram_labels_from_payload',
    'extract_formulas',
    'get_weights',
    'resolve_subject',
]
