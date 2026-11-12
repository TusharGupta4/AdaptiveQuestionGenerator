import re
from typing import Dict


try:
    from .. import config as grade_config
except ImportError:
    import config as grade_config


try:
    import sympy as _sympy
    from sympy import simplify, cos, sin
    from sympy.parsing.sympy_parser import (
        implicit_multiplication_application, parse_expr, split_symbols,
        standard_transformations, convert_xor,
    )
    SYMPY_AVAILABLE = True
except Exception:
    _sympy = None
    SYMPY_AVAILABLE = False


from .feature_extractors import (
    _diagram_labels_from_payload, _normalize_equation, _normalize_label_list,
    extract_equations, fuzzy_match_keyword,
)
DEFAULT_WEIGHTS = {
    'semantic': 0.40, 'fuzzy_keyword': 0.30,
    'word_count': 0.15, 'ocr_quality': 0.15,
}
SUBJECT_WEIGHTS = {
    'humanities': dict(DEFAULT_WEIGHTS),
    'stem': {'semantic': 0.25, 'fuzzy_keyword': 0.15,
             'equation_accuracy': 0.35, 'word_count': 0.10,
             'ocr_quality': 0.15},
    'diagram_based': {'semantic': 0.20, 'fuzzy_keyword': 0.15,
                      'diagram_label': 0.35, 'word_count': 0.15,
                      'ocr_quality': 0.15},
}


def _coerce_marks(value, default: float = 5.0) -> float:
    try:
        marks = float(value)
    except (TypeError, ValueError):
        return default
    return default if marks <= 0 else marks


def resolve_subject_type(subject_type=None, subject=None,
                         required_diagram_labels=None) -> str:
    def token(value):
        text = '' if value is None else str(value).strip().lower()
        return re.sub(r'[^a-z0-9]+', '_', text).strip('_')
    explicit, subject_token = token(subject_type), token(subject)
    stem = {'stem', 'math', 'maths', 'mathematics', 'physics', 'chemistry',
            'science', 'general_science', 'engineering', 'computer_science',
            'computer', 'coding', 'accountancy', 'statistics'}
    diagrams = {'diagram', 'diagrams', 'diagram_based', 'diagrammatic',
                'visual', 'visual_based', 'figure_based', 'drawing'}
    humanities = {'humanities', 'humanity', 'arts', 'english', 'history',
                  'geography', 'economics', 'polity', 'political_science',
                  'social_science', 'biology', 'commerce', 'sanskrit', 'hindi'}
    if explicit in diagrams:
        return 'diagram_based'
    if explicit in stem:
        return 'stem'
    if explicit in humanities:
        return 'humanities'
    if _normalize_label_list(required_diagram_labels):
        return 'diagram_based'
    if subject_token in diagrams:
        return 'diagram_based'
    return 'stem' if subject_token in stem else 'humanities'


def _apply_grade_profile_to_weights(weights: Dict[str, float],
                                    grade_profile=None) -> Dict[str, float]:
    adjusted = dict(weights)
    if not grade_profile:
        return adjusted
    grade_weights = grade_profile.get('weights') or {}
    for dimension in ('semantic', 'fuzzy_keyword', 'word_count', 'ocr_quality'):
        baseline = DEFAULT_WEIGHTS.get(dimension)
        grade_weight = grade_weights.get(dimension)
        if baseline and grade_weight is not None and dimension in adjusted:
            adjusted[dimension] *= float(grade_weight) / baseline
    total = sum(adjusted.values())
    if total <= 0:
        return dict(weights)
    normalized = {d: round(w / total, 6) for d, w in adjusted.items()}
    largest = max(normalized, key=normalized.get)
    normalized[largest] = round(normalized[largest] + (1.0 - sum(normalized.values())), 6)
    return normalized


def get_subject_weights(subject_type=None, subject=None,
                        required_diagram_labels=None,
                        selected_class=None) -> Dict[str, float]:
    """Return the dynamic weight matrix for the resolved subject type and grade."""
    resolved = resolve_subject_type(subject_type, subject, required_diagram_labels)
    weights = SUBJECT_WEIGHTS.get(resolved, DEFAULT_WEIGHTS)
    return _apply_grade_profile_to_weights(
        weights, grade_config.resolve_grade_profile(selected_class))
def compute_garbled_ratio(text: str) -> float:
    """Compute ratio of garbled tokens for OCR quality penalty"""
    if not text:
        return 1.0
    words = re.findall(r'\b\w+\b', text)
    if not words:
        return 1.0
    garbled = 0
    for w in words:
        if len(w) < 2 or (re.match(r'^[^aeiouAEIOU]{5,}$', w) and len(w) > 5):
            garbled += 1
    return garbled / len(words)
def _normalize_keywords(keywords) -> list:
    if isinstance(keywords, str):
        return [k.strip() for k in keywords.split(',') if k.strip()]
    if keywords:
        return [str(k).strip() for k in keywords if str(k).strip()]
    return []


def _sympy_expression(expression: str):
    text = _normalize_equation(expression).replace('^', '**')
    text = re.sub(r'\\(left|right|,|;|!)', '', text)
    text = re.sub(r'\\[a-zA-Z]+', '', text).replace('{', '(').replace('}', ')')
    left, right = text.split('=', 1) if '=' in text else (text, '0')
    transformations = standard_transformations + (
        implicit_multiplication_application, convert_xor, split_symbols)
    left_expr = parse_expr(left.strip(), transformations=transformations, evaluate=False)
    right_expr = parse_expr(right.strip(), transformations=transformations, evaluate=False)
    return _sympy.simplify(left_expr - right_expr)


def _sympy_equivalent(left_expression: str, right_expression: str) -> bool:
    if not SYMPY_AVAILABLE:
        return False
    try:
        left = _sympy_expression(left_expression)
        right = _sympy_expression(right_expression)
        if left == 0 or right == 0:
            return bool(left == right)
        if _sympy.simplify(left - right) == 0 or _sympy.simplify(left + right) == 0:
            return True
        ratio = _sympy.simplify(left / right)
        return bool(not getattr(ratio, 'free_symbols', set()))
    except Exception:
        return False


def _equation_similarity(reference: str, student: str) -> float:
    from difflib import SequenceMatcher
    ref_normalized = _normalize_equation(reference)
    student_normalized = _normalize_equation(student)
    if not ref_normalized or not student_normalized:
        return 0.0
    if ref_normalized == student_normalized or _sympy_equivalent(reference, student):
        return 1.0
    return SequenceMatcher(None, ref_normalized, student_normalized).ratio()


def _equation_accuracy(reference_text: str, student_text: str) -> tuple:
    reference_equations = extract_equations(reference_text)
    student_equations = extract_equations(student_text)
    if not reference_equations:
        return None, {'reference_equations': [], 'student_equations': student_equations,
                      'matched_equations': [], 'missing_equations': [],
                      'sympy_available': SYMPY_AVAILABLE}
    details, matched, missing, scores = [], [], [], []
    for reference in reference_equations:
        best_score, best_match = 0.0, ''
        for candidate in student_equations:
            score = _equation_similarity(reference, candidate)
            if score > best_score:
                best_score, best_match = score, candidate
        scores.append(best_score)
        is_match = best_score >= 0.85
        (matched if is_match else missing).append(reference)
        details.append({'reference': reference, 'student': best_match,
                        'score': best_score,
                        'status': 'matched' if is_match else 'missing_or_inaccurate'})
    accuracy = (sum(scores) / len(scores)) * 100.0
    return accuracy, {'reference_equations': reference_equations,
                      'student_equations': student_equations,
                      'matched_equations': matched, 'missing_equations': missing,
                      'comparisons': details, 'sympy_available': SYMPY_AVAILABLE}


def compute_dimension_scores(resolved_subject_type, reference_text,
                             student_text, required_diagram_labels, diagrams,
                             keyword_threshold, formal_term_validation):
    if resolved_subject_type == 'stem':
        equation_score, equation_details = _equation_accuracy(reference_text, student_text)
    else:
        equation_score = None
        equation_details = {'reference_equations': [], 'student_equations': [],
                            'matched_equations': [], 'missing_equations': [],
                            'sympy_available': SYMPY_AVAILABLE}
    required = _normalize_label_list(required_diagram_labels)
    detected = _diagram_labels_from_payload(diagrams)
    if not required:
        diagram_score = None
        diagram_details = {'required_labels': [], 'detected_labels': detected,
                           'matched_labels': [], 'missing_labels': [],
                           'diagram_source': 'none'}
    else:
        corpus = ' | '.join(detected) if detected else (student_text or '')
        source = 'diagrams' if detected else 'student_text_fallback'
        matched = [label for label in required if fuzzy_match_keyword(
            label, corpus, threshold=keyword_threshold, formal=formal_term_validation)]
        missing = [label for label in required if label not in matched]
        diagram_score = (len(matched) / len(required)) * 100.0
        diagram_details = {'required_labels': required, 'detected_labels': detected,
                           'matched_labels': matched, 'missing_labels': missing,
                           'diagram_source': source}
    return equation_score, equation_details, diagram_score, diagram_details


def compute_word_and_ocr_scores(student_text, min_words, word_count_tolerance,
                                word_count_penalty_scale):
    words = re.findall(r'\b\w+\b', student_text or '')
    word_count = len(words)
    min_words = max(0, int(min_words or 0))
    effective_min_words = min_words * (1.0 - word_count_tolerance)
    word_count_score = 100.0
    word_count_penalty_applied = False
    if effective_min_words > 0 and word_count < effective_min_words:
        penalty = ((effective_min_words - word_count) / effective_min_words * 50) * word_count_penalty_scale
        word_count_score = max(0, 100 - penalty)
        word_count_penalty_applied = True
    garbled_ratio = compute_garbled_ratio(student_text or '')
    ocr_quality_score = 100.0
    ocr_penalty_applied = False
    if garbled_ratio > 0.1:
        ocr_quality_score = max(0, 100 - garbled_ratio * 50)
        ocr_penalty_applied = True
    return {'word_count': word_count, 'effective_min_words': effective_min_words,
            'word_count_score': word_count_score,
            'word_count_penalty_applied': word_count_penalty_applied,
            'garbled_ratio': garbled_ratio, 'ocr_quality_score': ocr_quality_score,
            'ocr_penalty_applied': ocr_penalty_applied}


def compute_reference_scores(student_text, reference_text, keyword_list,
                             keyword_threshold, formal_term_validation,
                             equation_score, resolved_subject_type,
                             diagram_score, word_count_score, ocr_quality_score):
    from .feature_extractors import cosine_similarity, get_embeddings, keyword_match_ratio
    try:
        embeddings = get_embeddings([student_text, reference_text])
        emb_sim = (cosine_similarity(embeddings[0], embeddings[1])
                   if len(embeddings) == 2 and embeddings[0] and embeddings[1] else 0.0)
    except Exception:
        emb_sim = 0.0
    semantic_score = emb_sim * 100
    kw_ratio = keyword_match_ratio(student_text, reference_text, keyword_list,
                                   threshold=keyword_threshold,
                                   formal=formal_term_validation)
    fuzzy_keyword_score = kw_ratio * 100
    sub_scores = {'semantic': semantic_score, 'fuzzy_keyword': fuzzy_keyword_score,
                  'word_count': word_count_score, 'ocr_quality': ocr_quality_score}
    if equation_score is not None or resolved_subject_type == 'stem':
        sub_scores['equation_accuracy'] = equation_score
    if diagram_score is not None or resolved_subject_type == 'diagram_based':
        sub_scores['diagram_label'] = diagram_score
    return emb_sim, semantic_score, kw_ratio, fuzzy_keyword_score, sub_scores


def compute_weighted_score(sub_scores, weights):
    available_weights = {name: weight for name, weight in weights.items()
                         if sub_scores.get(name) is not None and weight > 0}
    if not available_weights:
        available_weights = {'semantic': 1.0}
    total_weight = sum(available_weights.values())
    effective_weights = {name: weight / total_weight for name, weight in available_weights.items()}
    weighted_score = sum(sub_scores[name] * weight for name, weight in effective_weights.items())
    return weighted_score, effective_weights
