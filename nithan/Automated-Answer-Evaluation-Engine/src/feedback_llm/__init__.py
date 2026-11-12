from .core import (
    LAST_INFERENCE_MODE,
    _coerce_estimated_marks,
    _ensure_sentence_end,
    _estimated_marks_from_text,
    _finalize_feedback,
    _parse_zero_shot_response,
    _string_field_from_text,
    generate_feedback,
    generate_feedback_result,
    re_split_sentences,
)
from .llm_client import (
    DEFAULT_MODEL_NAME,
    OLLAMA_MODELS,
    _build_prompt,
    _call_groq,
    _call_ollama,
    _deterministic_feedback,
    _parse_json_response,
    _response_text,
)

generate_feedback_report = generate_feedback
create_feedback = generate_feedback
get_feedback = generate_feedback


def __getattr__(name):
    if name == 'LAST_INFERENCE_MODE':
        from . import core
        return core.LAST_INFERENCE_MODE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
