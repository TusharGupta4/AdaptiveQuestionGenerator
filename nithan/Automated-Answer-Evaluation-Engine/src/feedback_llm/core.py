import logging, math, os, re, sys
from typing import List

try:
    from .. import config as grade_config
except ImportError:
    import config as grade_config

from . import llm_client
from .llm_client import _parse_json_response

logger = logging.getLogger(__name__)
LAST_INFERENCE_MODE = None

def _coerce_estimated_marks(value, max_marks: float):
    try:
        marks = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(marks) or marks < 0:
        return None
    return min(max(marks, 0.0), max_marks)

def _estimated_marks_from_text(response_text: str, max_marks: float):
    match = re.search(
        r'["\']?estimated_marks["\']?\s*[:=]\s*["\']?'
        r'(\d+(?:\.\d+)?)',
        response_text or '',
        flags=re.IGNORECASE,
    )
    if not match:
        return None
    return _coerce_estimated_marks(match.group(1), max_marks)

def _string_field_from_text(response_text: str, field: str) -> str:
    """Salvage a string field even when the surrounding JSON is truncated."""
    match = re.search(
        r'"' + re.escape(field) + r'"\s*:\s*"',
        response_text or '',
        flags=re.IGNORECASE,
    )
    if not match:
        return ''
    value = []
    escaped = False
    for character in response_text[match.end():]:
        if escaped:
            value.append(character)
            escaped = False
        elif character == '\\':
            escaped = True
        elif character == '"':
            break
        else:
            value.append(character)
    return ''.join(value).strip().rstrip('}').strip()

def _ensure_sentence_end(sentence: str) -> str:
    sentence = (sentence or '').strip()
    if sentence and not re.search(r'[.!?]$', sentence):
        sentence += '.'
    return sentence


_SENTENCE_ABBREVIATIONS = (
    'e.g.', 'i.e.', 'vs.', 'Mr.', 'Mrs.', 'Ms.', 'Dr.', 'Prof.',
    'St.', 'No.', 'Fig.', 'Figs.', 'Eq.', 'Eqs.', 'approx.', 'cf.', 'viz.',
)

def re_split_sentences(text):
    protected = str(text or '')
    placeholders = {}
    for index, abbreviation in enumerate(_SENTENCE_ABBREVIATIONS):
        placeholder = f'__ABBR_{index}__'
        placeholders[placeholder] = abbreviation
        protected = re.sub(
            r'(?<!\w)' + re.escape(abbreviation),
            placeholder,
            protected,
            flags=re.IGNORECASE,
        )
    sentences = re.split(r'(?<=[.!?])\s+', protected)
    restored = []
    for sentence in sentences:
        for placeholder, abbreviation in placeholders.items():
            sentence = sentence.replace(placeholder, abbreviation)
        if sentence.strip():
            restored.append(sentence)
    return restored

def _finalize_feedback(feedback: str, zero_shot: bool,
                       missing_keywords: List[str]) -> str:
    feedback = (feedback or '').strip()
    if not feedback:
        return ''
    sentences = re_split_sentences(feedback)
    if len(sentences) >= 2:
        return (
            _ensure_sentence_end(sentences[0])
            + ' '
            + _ensure_sentence_end(sentences[1])
        )
    if len(sentences) == 1:
        sentence = _ensure_sentence_end(sentences[0])
        if zero_shot:
            return sentence + " To improve, focus on making the answer more complete and logically structured."
        if missing_keywords:
            return sentence + f" To improve, focus on incorporating concepts like {', '.join(missing_keywords[:2])}."
        return sentence + " Adding more specific details would further strengthen your answer."
    return feedback

def _parse_zero_shot_response(response_text: str, max_marks: float,
                              missing_keywords: List[str]) -> dict:
    payload = _parse_json_response(response_text)
    feedback = ''
    estimated_marks = None
    parsed_json = False
    if isinstance(payload, dict):
        for field in ('qualitative_feedback', 'feedback', 'assessment', 'reasoning'):
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                feedback = value.strip()
                break
        if not feedback:
            feedback = _string_field_from_text(response_text, 'qualitative_feedback')
        estimated_marks = _coerce_estimated_marks(
            payload.get('estimated_marks')
            if payload.get('estimated_marks') is not None
            else payload.get('awarded_marks'),
            max_marks,
        )
        parsed_json = bool(feedback)
    else:
        estimated_marks = _estimated_marks_from_text(response_text, max_marks)
        feedback = _string_field_from_text(
            response_text, 'qualitative_feedback') or response_text
    if not feedback:
        return {}
    return {
        'qualitative_feedback': _finalize_feedback(feedback, True, missing_keywords),
        'estimated_marks': estimated_marks,
        'max_marks': max_marks,
        'parsed_json': parsed_json,
    }

def _dispatch_llm(name, *args, **kwargs):
    package = sys.modules.get(__package__)
    implementation = getattr(package, name, None) if package else None
    if implementation is None:
        implementation = getattr(llm_client, name)
    return implementation(*args, **kwargs)

def _set_inference_mode(mode):
    global LAST_INFERENCE_MODE
    LAST_INFERENCE_MODE = mode
    package = sys.modules.get(__package__)
    if package is not None:
        package.LAST_INFERENCE_MODE = mode

def generate_feedback_result(student_score: float = None, missing_keywords: List[str] = None,
                             reference_answer: str = "", student_answer: str = "",
                             awarded_marks: float = None, max_marks: float = None,
                             recognized_concepts: List[str] = None, has_reference: bool = True,
                             scoring_mode: str = None, question_text: str = "",
                             selected_class=None) -> dict:
    """
    Generate feedback plus structured zero-shot marks using a hybrid path.

    Zero-shot responses are requested as strict JSON so the UI can safely show
    ``estimated_marks`` instead of leaving the marks field pending. The legacy
    :func:`generate_feedback` string API is preserved for compatibility.
    """
    if missing_keywords is None:
        missing_keywords = []
    if recognized_concepts is None:
        recognized_concepts = []
    grade_profile = grade_config.resolve_grade_profile(selected_class)
    zero_shot = (scoring_mode == "zero_shot_llm") or (has_reference is False)
    max_marks_value = max_marks if max_marks is not None else 5.0
    score = student_score
    if score is not None and score > 1.0:
        score = score / 100.0
    score_percent = round(score * 100, 1) if score is not None else 0
    marks_info = ""
    if awarded_marks is not None and max_marks is not None:
        marks_info = f"awarded {awarded_marks:.1f} out of {max_marks} marks"
    prompt = llm_client._build_prompt(
        zero_shot, score_percent, marks_info, recognized_concepts,
        missing_keywords, reference_answer, student_answer, question_text,
        max_marks_value, grade_profile,
    )
    model_name = os.getenv('MODEL_NAME', llm_client.DEFAULT_MODEL_NAME)
    raw_feedback = ''
    if model_name:
        raw_feedback = _dispatch_llm('_call_groq', prompt, model_name, grade_profile)
        if raw_feedback:
            _set_inference_mode(f"Groq API ({model_name})")
            logger.info("Inference Mode: Groq API (%s)", model_name)
    if not raw_feedback:
        raw_feedback = _dispatch_llm('_call_ollama', prompt)
        if raw_feedback:
            _set_inference_mode("Local Ollama Fallback")
            logger.info("Inference Mode: Local Ollama Fallback")
    feedback = ''
    estimated_marks = None
    parsed_json = False
    if raw_feedback:
        if zero_shot:
            parsed = _parse_zero_shot_response(
                raw_feedback, max_marks_value, missing_keywords)
            if parsed:
                feedback = parsed['qualitative_feedback']
                estimated_marks = parsed['estimated_marks']
                parsed_json = parsed['parsed_json']
        else:
            feedback = _finalize_feedback(
                raw_feedback, zero_shot, missing_keywords)
    if not feedback:
        _set_inference_mode("Deterministic Fallback")
        logger.info("Inference Mode: Deterministic Fallback")
        feedback = llm_client._deterministic_feedback(
            zero_shot, score, score_percent, marks_info, missing_keywords,
            max_marks_value, grade_profile,
        )
    return {
        'qualitative_feedback': feedback,
        'feedback': feedback,
        'estimated_marks': estimated_marks,
        'awarded_marks': estimated_marks if zero_shot else awarded_marks,
        'max_marks': max_marks_value,
        'parsed_json': parsed_json,
        'zero_shot': zero_shot,
        'inference_mode': LAST_INFERENCE_MODE,
        'raw_response': raw_feedback,
    }

def generate_feedback(student_score: float = None, missing_keywords: List[str] = None,
                      reference_answer: str = "", student_answer: str = "",
                      awarded_marks: float = None, max_marks: float = None,
                      recognized_concepts: List[str] = None, has_reference: bool = True,
                      scoring_mode: str = None, question_text: str = "",
                      selected_class=None) -> str:
    """Backwards-compatible string-returning feedback API."""
    return generate_feedback_result(
        student_score, missing_keywords, reference_answer, student_answer,
        awarded_marks, max_marks, recognized_concepts, has_reference,
        scoring_mode, question_text, selected_class)['qualitative_feedback']
