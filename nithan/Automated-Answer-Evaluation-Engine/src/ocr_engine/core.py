import sys
import json
import re
from typing import Any, Dict, List, Optional

import pytesseract
from PIL import Image

from src import document_parser
import src.ocr_engine as ocr_pkg
from .diagram_utils import normalize_diagrams
from .formatters import (
    _item_text,
    _json_objects_from_text,
    normalize_formula_list,
    normalize_question_key,
    normalize_smiles,
)
from .groq_client import extract_with_groq

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except Exception:
    EASYOCR_AVAILABLE = False

UNIFIED_DOCUMENT_FIELDS = (
    'student_answer', 'document_text', 'raw_text', 'transcript',
    'unified_text', 'full_text', 'text',
)


# ---------------------------------------------------------------------------
# OCR Confidence & Fallback Helpers
# ---------------------------------------------------------------------------

def _confidence_result(
    text: str, confidences: List[float], method: str, engine: str
) -> Dict[str, Any]:
    """Formats standardized OCR result payloads with illegibility flags."""
    average = sum(confidences) / len(confidences) if confidences else 0.0
    illegible = average < 40.0
    return {
        'text': text,
        'full_text': text,
        'average_confidence': average,
        'avg_confidence': average,
        'confidence': average,
        'confidences': confidences,
        'is_illegible': illegible,
        'illegible': illegible,
        'below_threshold': illegible,
        'method': method,
        'engine': engine,
    }


def extract_with_easyocr(image: Image.Image) -> Optional[Dict[str, Any]]:
    """Offline OCR fallback using EasyOCR."""
    if not EASYOCR_AVAILABLE:
        return None
    try:
        import numpy as np
        reader = easyocr.Reader(['en'], gpu=False)
        results = reader.readtext(np.array(image), canvas_size=1280, paragraph=False)
        texts = [text for _, text, _ in results]
        confidences = [confidence * 100 for _, _, confidence in results]
        return _confidence_result('\n'.join(texts), confidences, 'easyocr', 'EasyOCR Fallback')
    except Exception:
        return None


def extract_text_with_confidence(
    image: Image.Image,
    use_groq: bool = True,
    page_number: Optional[int] = None,
    total_pages: Optional[int] = None,
    prior_question_ids: Optional[List[str]] = None,
    subject_type: Optional[str] = None,
    subject: Optional[str] = None,
    include_smiles: Optional[bool] = None,
) -> Dict[str, Any]:
    """Primary OCR orchestrator using Groq VLM with EasyOCR & Tesseract fallbacks."""
    if use_groq:
        result = extract_with_groq(
            image,
            page_number=page_number,
            total_pages=total_pages,
            prior_question_ids=prior_question_ids,
            subject_type=subject_type,
            subject=subject,
            include_smiles=include_smiles,
        )
        if result:
            return result

    # 1. Secondary Offline Fallback: EasyOCR
    easy_result = extract_with_easyocr(image)
    if easy_result:
        return easy_result

    # 2. Tertiary Offline Fallback: Tesseract
    try:
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        confidences = []
        for confidence in data.get('conf', []):
            try:
                val = float(confidence)
                if val >= 0:
                    confidences.append(val)
            except (ValueError, TypeError):
                continue
        text = pytesseract.image_to_string(image)
        return _confidence_result(text, confidences, 'tesseract', 'Tesseract Fallback')
    except Exception:
        return _confidence_result('', [], 'none', 'None')


# ---------------------------------------------------------------------------
# Document & Multi-Page Assembly
# ---------------------------------------------------------------------------

def assemble_page_texts(page_texts: List[str]) -> str:
    """Joins page transcripts into a single ordered document string."""
    blocks = [
        str(text).strip()
        for text in (page_texts or [])
        if isinstance(text, str) and text.strip()
    ]
    return '\n\n'.join(blocks).strip()


def extract_document_from_pages(images: List[Image.Image], use_groq: bool = True,
                                subject_type: str = None,
                                subject: str = None,
                                include_smiles: bool = None) -> Dict:
    """Run OCR over every page first, then assemble one unified document string."""
    total_pages = len(images or [])
    page_texts, page_results = [], []
    all_diagrams, all_smiles, all_latex = [], [], []
    
    extractor = getattr(ocr_pkg, 'extract_text_with_confidence', extract_text_with_confidence)

    for index, image in enumerate(images or []):
        result = extractor(
            image, use_groq=use_groq, page_number=index + 1,
            total_pages=total_pages, subject_type=subject_type,
            subject=subject, include_smiles=include_smiles)
        unified = (
            result.get('student_answer') or result.get('markdown')
            or result.get('unified_text'))
        raw_text = unified or result.get('text', result.get('full_text', ''))
        text = unified or extract_unified_text(raw_text)
        diagrams = normalize_diagrams(result.get('diagrams') or [])
        smiles = normalize_smiles(result.get('smiles') or [])
        latex = normalize_formula_list(
            result.get('latex_formulas') or result.get('formulas')
            or result.get('equations') or [])
        for diagram in diagrams:
            diagram.setdefault('page_number', index + 1)
            all_diagrams.append(diagram)
        all_smiles.extend(smiles)
        all_latex.extend(latex)
        page_texts.append(text)
        page_results.append({
            'page_number': index + 1, 'text': text, 'raw_text': raw_text,
            'diagrams': diagrams, 'smiles': smiles,
            'latex_formulas': latex, 'result': result})
    full_text = assemble_page_texts(page_texts)
    return {
        'full_text': full_text, 'document_text': full_text,
        'page_texts': page_texts, 'page_results': page_results,
        'diagrams': all_diagrams, 'smiles': normalize_smiles(all_smiles),
        'smiles_strings': normalize_smiles(all_smiles),
        'latex_formulas': normalize_formula_list(all_latex),
        'formulas': normalize_formula_list(all_latex),
        'total_pages': total_pages,
    }


def extract_full_document_text(
    images: List[Image.Image],
    use_groq: bool = True,
    subject_type: Optional[str] = None,
    subject: Optional[str] = None,
    include_smiles: Optional[bool] = None,
) -> str:
    """Convenience wrapper returning only the unified multi-page transcript string."""
    doc = extract_document_from_pages(
        images,
        use_groq=use_groq,
        subject_type=subject_type,
        subject=subject,
        include_smiles=include_smiles,
    )
    return doc['full_text']


# ---------------------------------------------------------------------------
# Question Extraction & Payload Parsing
# ---------------------------------------------------------------------------

def extract_full_document_questions(
    full_document_text: str,
    expected_question_ids: Optional[List[str]] = None,
    use_groq: bool = True,
) -> Dict[str, str]:
    """Extracts question-to-answer block mappings from full document text."""
    if not full_document_text or not str(full_document_text).strip():
        return {}

    expected = [
        normalize_question_key(qid)
        for qid in (expected_question_ids or [])
        if normalize_question_key(qid)
    ]

    # Standard fallback regex parser from document_parser
    parsed = document_parser.extract_question_blocks(full_document_text, expected)

    if expected:
        parsed = {
            qid: text
            for qid, text in parsed.items()
            if qid in expected or qid.startswith('Q')
        }
    return {qid: text for qid, text in parsed.items() if text}


def process_document(
    images: List[Image.Image],
    expected_question_ids: Optional[List[str]] = None,
    use_groq: bool = True,
    subject_type: Optional[str] = None,
    subject: Optional[str] = None,
    include_smiles: Optional[bool] = None,
) -> Dict[str, Any]:
    """Full pipeline runner: page OCR, unified text assembly, and question extraction."""
    document = extract_document_from_pages(
        images,
        use_groq=use_groq,
        subject_type=subject_type,
        subject=subject,
        include_smiles=include_smiles,
    )
    questions = extract_full_document_questions(
        document['full_text'], expected_question_ids, use_groq=use_groq
    )
    document['questions'] = questions
    document['question_blocks'] = questions
    return document


def _extract_answer_items(payload: Any) -> List[Any]:
    """Helper to pull raw question/answer items out of diverse JSON response shapes."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    for field in ('answers', 'questions', 'data', 'results'):
        value = payload.get(field)
        if isinstance(value, list) and value:
            return value
        if isinstance(value, dict) and value:
            return [
                {'question_number': k, 'extracted_text': v}
                for k, v in value.items()
            ]

    for field in UNIFIED_DOCUMENT_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return [{'question_number': 'Q1', 'extracted_text': value}]

    items = []
    for key, value in payload.items():
        if isinstance(value, str):
            items.append({'question_number': key, 'extracted_text': value})
        elif isinstance(value, dict):
            item = dict(value)
            item.setdefault('question_number', key)
            items.append(item)
    return items


def extract_unified_text(vlm_response_text: str) -> str:
    """Converts structured VLM JSON responses into a continuous document string."""
    if not vlm_response_text:
        return ''
    raw = str(vlm_response_text).strip()
    if not raw:
        return ''

    cleaned = re.sub(r'```(?:json)?', '', raw, flags=re.IGNORECASE).strip()

    def _from_payload(payload: Any) -> str:
        if isinstance(payload, dict):
            for field in UNIFIED_DOCUMENT_FIELDS:
                val = payload.get(field)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        texts = [_item_text(item) for item in _extract_answer_items(payload)]
        return '\n'.join(text for text in texts if text).strip()

    for candidate in (raw, cleaned):
        try:
            return _from_payload(json.loads(candidate))
        except json.JSONDecodeError:
            continue

    objects = _json_objects_from_text(cleaned)
    if objects:
        blocks = [_from_payload(obj) for obj in objects]
        merged = '\n'.join(block for block in blocks if block).strip()
        if merged:
            return merged

    return cleaned