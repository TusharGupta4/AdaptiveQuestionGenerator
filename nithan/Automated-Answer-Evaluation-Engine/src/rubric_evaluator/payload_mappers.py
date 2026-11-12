from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple, Union

from src import document_parser
from .feature_extractors import (
    cosine_similarity,
    get_embeddings,
    keyword_match_ratio,
)
from .scoring import _coerce_marks


# ---------------------------------------------------------------------------
# Block Normalization & Coercion
# ---------------------------------------------------------------------------

def _coerce_block_map(blocks: Any) -> Dict[str, str]:
    """Normalizes a block mapping or list into standard ``{"Q1": "text", ...}`` format."""
    result: Dict[str, str] = {}
    if isinstance(blocks, dict):
        items = list(blocks.items())
    elif isinstance(blocks, (list, tuple)):
        items = [(f"Q{index + 1}", block) for index, block in enumerate(blocks)]
    else:
        return result

    for key, value in items:
        if isinstance(value, dict):
            text = (
                value.get('text')
                or value.get('answer')
                or value.get('student_answer')
                or value.get('extracted_text')
                or value.get('content')
                or ''
            )
        else:
            text = value

        text = str(text or '').strip()
        if not text:
            continue

        qid = document_parser.normalize_question_key(key)
        if not qid:
            continue

        result[qid] = f"{result[qid]}\n{text}".strip() if qid in result else text

    return result


# ---------------------------------------------------------------------------
# Semantic Matching & Question Mapping
# ---------------------------------------------------------------------------

def find_best_semantic_block(
    question_text: str, blocks: Any, threshold: float = 0.30
) -> Dict[str, Any]:
    """
    Finds the answer block that best matches a question.
    Uses semantic embeddings when available, falling back to fuzzy keyword ratio.
    """
    block_map = _coerce_block_map(blocks)
    question_text = str(question_text or '').strip()
    empty = {'key': '', 'text': '', 'score': 0.0, 'matched': False}

    if not block_map or not question_text:
        return empty

    keys = list(block_map.keys())
    texts = [block_map[key] for key in keys]
    embedding_scores = [0.0] * len(texts)

    try:
        embeddings = get_embeddings([question_text] + texts)
        if len(embeddings) == len(texts) + 1 and embeddings[0]:
            for index, embedding in enumerate(embeddings[1:]):
                if embedding:
                    similarity = cosine_similarity(embeddings[0], embedding)
                    embedding_scores[index] = max(0.0, min(1.0, similarity))
    except Exception:
        pass

    best_index, best_score = 0, -1.0
    for index, text in enumerate(texts):
        try:
            keyword_score = keyword_match_ratio(text, question_text)
        except Exception:
            keyword_score = 0.0

        sequence_score = SequenceMatcher(
            None, question_text.lower(), text.lower()
        ).ratio()
        score = max(embedding_scores[index], keyword_score, sequence_score)
        if score > best_score:
            best_score, best_index = score, index

    best_score = max(0.0, float(best_score))
    return {
        'key': keys[best_index],
        'text': texts[best_index],
        'score': best_score,
        'matched': best_score >= threshold,
    }


def match_questions_to_blocks(
    questions: Any,
    blocks: Any,
    threshold: float = 0.30,
    allow_reuse: bool = False,
) -> Dict[str, Dict[str, Any]]:
    """Matches CSV/Loader questions to available student answer text blocks."""
    block_map = _coerce_block_map(blocks)

    if isinstance(questions, dict):
        question_items = []
        for key, value in questions.items():
            if isinstance(value, dict):
                item = dict(value)
                item.setdefault('question_no', key)
            else:
                item = {'question_no': key, 'question_text': str(value or '')}
            question_items.append(item)
    else:
        question_items = list(questions or [])

    prepared = []
    for question in question_items:
        if isinstance(question, dict):
            raw_id = (
                question.get('question_no')
                or question.get('question_id')
                or question.get('question_number')
                or question.get('id')
            )
            qtext = str(
                question.get('question_text')
                or question.get('question')
                or question.get('prompt')
                or ''
            ).strip()
        else:
            raw_id, qtext = question, ''

        qid = document_parser.normalize_question_key(raw_id)
        if qid:
            prepared.append((qid, qtext))

    result: Dict[str, Dict[str, Any]] = {}
    missing = []

    for qid, qtext in prepared:
        direct = block_map.get(qid, '')
        if direct.strip():
            result[qid] = {
                'question_id': qid,
                'text': direct,
                'score': 1.0,
                'matched': True,
                'source': 'tag',
                'matched_block': qid,
            }
        else:
            missing.append((qid, qtext))

    used_blocks = {
        match['matched_block']
        for match in result.values()
        if match.get('matched_block')
    }

    for qid, qtext in missing:
        candidates = (
            block_map
            if allow_reuse
            else {k: v for k, v in block_map.items() if k not in used_blocks}
        )
        match = find_best_semantic_block(qtext or qid, candidates, threshold)
        if match['matched']:
            result[qid] = {
                'question_id': qid,
                'text': match['text'],
                'score': match['score'],
                'matched': True,
                'source': 'semantic',
                'matched_block': match['key'],
            }
            used_blocks.add(match['key'])
        else:
            result[qid] = {
                'question_id': qid,
                'text': '',
                'score': match['score'],
                'matched': False,
                'source': 'zero_shot',
                'matched_block': '',
            }

    return result


def compute_cosine_similarity(text1: str, text2: str) -> float:
    """Computes cosine similarity between two text string embeddings."""
    try:
        embeddings = get_embeddings([text1, text2])
        if len(embeddings) == 2 and embeddings[0] and embeddings[1]:
            return cosine_similarity(embeddings[0], embeddings[1])
    except Exception:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# Result Builders & Context Resolvers
# ---------------------------------------------------------------------------

def build_subject_fields(
    resolved_subject_type: Any,
    weights: Any,
    equation_score: Any,
    equation_details: Any,
    diagram_score: Any,
    diagram_details: Any,
    sympy_available: bool,
) -> Dict[str, Any]:
    """Formats standardized subject-specific evaluation metrics."""
    return {
        'subject_type': resolved_subject_type,
        'weights': weights,
        'weight_matrix': weights,
        'equation_score': equation_score,
        'equation_accuracy': equation_score,
        'equation_details': equation_details,
        'sympy_available': sympy_available,
        'diagram_label_score': diagram_score,
        'diagram_label_match': (
            diagram_score / 100.0 if diagram_score is not None else None
        ),
        'diagram_labels_required': diagram_details['required_labels'],
        'diagram_labels_detected': diagram_details['detected_labels'],
        'diagram_labels_matched': diagram_details['matched_labels'],
        'diagram_labels_missing': diagram_details['missing_labels'],
        'diagram_details': diagram_details,
    }


def build_grade_fields(
    selected_class: Any,
    grade_profile: Any,
    keyword_threshold: Any,
    formal_term_validation: Any,
    word_count_tolerance: Any,
    effective_min_words: Any,
    word_count_penalty_scale: Any,
) -> Dict[str, Any]:
    """Formats grade profile and band configuration fields."""
    return {
        'selected_class': selected_class,
        'grade_profile': grade_profile['key'] if grade_profile else None,
        'grade_profile_label': grade_profile['label'] if grade_profile else None,
        'grade_band': grade_profile['class_band'] if grade_profile else None,
        'keyword_threshold': keyword_threshold,
        'formal_term_validation': formal_term_validation,
        'word_count_tolerance': word_count_tolerance,
        'effective_min_words': effective_min_words,
        'word_count_penalty_scale': word_count_penalty_scale,
    }


def build_zero_shot_result(
    fallback_max_marks: Any,
    word_count: int,
    word_count_score: Any,
    word_count_penalty_applied: bool,
    garbled_ratio: float,
    ocr_quality_score: float,
    ocr_penalty_applied: bool,
    zero_shot_sub_scores: Any,
    subject_fields: Dict[str, Any],
    grade_fields: Dict[str, Any],
) -> Dict[str, Any]:
    """Formats output dictionary payload for zero-shot LLM evaluation mode."""
    return {
        'score': None,
        'combined_score': None,
        'total_score': None,
        'awarded_marks': None,
        'marks_awarded': None,
        'max_marks': fallback_max_marks,
        'has_reference': False,
        'scoring_mode': 'zero_shot_llm',
        'reference_available': False,
        'semantic_similarity': None,
        'semantic_score': None,
        'fuzzy_keyword_coverage': None,
        'fuzzy_keyword_score': None,
        'keyword_match_ratio': None,
        'word_count': word_count,
        'word_count_score': word_count_score,
        'word_count_penalty_applied': word_count_penalty_applied,
        'garbled_ratio': garbled_ratio,
        'ocr_quality_score': ocr_quality_score,
        'ocr_penalty_applied': ocr_penalty_applied,
        'sub_scores': zero_shot_sub_scores,
        **subject_fields,
        **grade_fields,
    }


def build_reference_result(
    weighted_score: float,
    awarded_marks: float,
    resolved_max_marks: float,
    emb_sim: Any,
    semantic_score: Any,
    kw_ratio: Any,
    fuzzy_keyword_score: Any,
    word_count: int,
    word_count_score: Any,
    word_count_penalty_applied: bool,
    garbled_ratio: float,
    ocr_quality_score: float,
    ocr_penalty_applied: bool,
    sub_scores: Any,
    effective_weights: Any,
    subject_fields: Dict[str, Any],
    grade_fields: Dict[str, Any],
) -> Dict[str, Any]:
    """Formats output dictionary payload for reference-backed rubric evaluation mode."""
    return {
        'score': weighted_score / 100.0,
        'combined_score': weighted_score / 100.0,
        'total_score': weighted_score / 100.0,
        'awarded_marks': awarded_marks,
        'marks_awarded': awarded_marks,
        'max_marks': resolved_max_marks,
        'has_reference': True,
        'scoring_mode': 'rubric',
        'reference_available': True,
        'semantic_similarity': emb_sim,
        'semantic_score': semantic_score,
        'fuzzy_keyword_coverage': kw_ratio,
        'fuzzy_keyword_score': fuzzy_keyword_score,
        'keyword_match_ratio': kw_ratio,
        'word_count': word_count,
        'word_count_score': word_count_score,
        'word_count_penalty_applied': word_count_penalty_applied,
        'garbled_ratio': garbled_ratio,
        'ocr_quality_score': ocr_quality_score,
        'ocr_penalty_applied': ocr_penalty_applied,
        'sub_scores': sub_scores,
        'weights_used': effective_weights,
        **subject_fields,
        **grade_fields,
    }


def resolve_question_context(
    question: Optional[Dict[str, Any]],
    diagrams: Optional[List[Dict[str, Any]]],
    selected_class: Optional[str],
    default_max_marks: float,
) -> Dict[str, Any]:
    """Extracts normalized question metadata, diagrams, and reference answer context."""
    question = question or {}
    selected_class = (
        selected_class
        or question.get('class_name')
        or question.get('class')
    )
    reference = (
        question.get('reference_ans')
        or question.get('reference_answer')
        or question.get('reference')
        or ''
    )
    keywords = (
        question.get('key_words')
        or question.get('keywords')
        or question.get('keyword')
        or []
    )
    max_marks = question.get('max_marks')
    if max_marks is None:
        max_marks = question.get('marks')

    subject_type = (
        question.get('subject_type')
        or question.get('paper_type')
        or question.get('paper_category')
        or question.get('category')
        or question.get('stream')
        or ''
    )
    required_diagram_labels = (
        question.get('required_diagram_labels')
        or question.get('required_diagram_label_list')
        or question.get('diagram_labels')
        or question.get('required_labels')
        or []
    )

    if diagrams is None:
        diagrams = (
            question.get('diagrams')
            or question.get('detected_diagrams')
            or question.get('visuals')
            or []
        )

    return {
        'selected_class': selected_class,
        'reference': reference,
        'keywords': keywords,
        'subject_type': subject_type,
        'required_diagram_labels': required_diagram_labels,
        'diagrams': diagrams,
        'resolved_max_marks': _coerce_marks(max_marks, default_max_marks),
    }
