"""
OCR Engine Package Entrypoint.
Re-exports public entrypoints, convenience functions, and legacy aliases.
"""

from src import document_parser
from .core import (
    EASYOCR_AVAILABLE,
    UNIFIED_DOCUMENT_FIELDS,
    _confidence_result,
    _extract_answer_items,
    assemble_page_texts,
    extract_document_from_pages,
    extract_full_document_questions,
    extract_full_document_text,
    extract_text_with_confidence,
    extract_unified_text,
    extract_with_easyocr,
    process_document,
)
from .diagram_utils import (
    _append_missing_diagram_markers,
    _diagram_signature,
    _inline_diagram_blocks,
    _quote_diagram_value,
    _strip_inline_value,
    extract_diagram_labels,
    format_diagram_marker,
    merge_diagram_lists,
    normalize_diagrams,
    parse_inline_diagrams,
)
from .formatters import (
    _answers_from_payload,
    _as_text,
    _inline_labels,
    _item_key,
    _item_text,
    _json_objects_from_text,
    _merge_blocks,
    normalize_formula_list,
    normalize_label_list,
    normalize_question_key,
    normalize_smiles,
    parse_question_headers,
    parse_vlm_json_output,
)
from .groq_client import (
    CHEMISTRY_HINTS,
    _extract_body_text,
    _parse_json_payload,
    extract_with_groq,
    image_to_base64,
    is_chemistry_subject,
    parse_questions_with_groq,
)

SMILES_HINTS = ('smiles', 'structure', 'chemical structure')

# Public API & Backward-Compatible Aliases
parse_answers_by_question = parse_vlm_json_output
parse_headers = parse_question_headers
assemble_document = assemble_page_texts
assemble_pages = assemble_page_texts
extract_document_text = extract_full_document_text
ocr_pages_to_document = extract_full_document_text
ingest_document = process_document
run_document_ocr = process_document
parse_document_questions = extract_full_document_questions
parse_full_document_questions = extract_full_document_questions
extract_document_questions = extract_full_document_questions
extract_question_blocks = document_parser.extract_question_blocks
split_document_by_questions = document_parser.extract_question_blocks


def ocr_image(image):
    return extract_text_with_confidence(image)


def ocr_images(images):
    return [extract_text_with_confidence(image) for image in images]


def extract_text_with_ollama_vision(image):
    return None


def get_confidence(result):
    return result.get('average_confidence', result.get('confidence', 0.0))


def is_illegible_text(result):
    return result.get('is_illegible', result.get('below_threshold', False))