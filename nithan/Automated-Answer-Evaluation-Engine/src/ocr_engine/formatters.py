import ast
import json
import re
from typing import Any, Dict, List, Optional, Set

from src import document_parser


# String & Type Helpers

def _as_text(value: Any) -> str:
    """Safely converts primitive values to stripped strings."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    return ""


def normalize_question_key(key: Any) -> str:
    """Normalizes question keys into standard canonical format (e.g., 'Q1', 'Q2')."""
    if key is None:
        return ""
    if isinstance(key, (int, float)) and not isinstance(value, bool):
        return f"Q{int(key)}"

    value = str(key).strip()
    if not value:
        return ""

    match = re.search(r"(?i)\bq(?:uestion)?\s*[_\-:#.)\]\s]*(\d+)\b", value)
    if not match:
        match = re.search(r"\b(\d+)\b", value)

    return f"Q{int(match.group(1))}" if match else value.upper()


def _merge_blocks(existing: str, new_text: str) -> str:
    """Appends new text blocks separated by newlines."""
    existing = (existing or "").strip()
    new_text = (new_text or "").strip()

    if not existing:
        return new_text
    if not new_text or new_text in existing:
        return existing
    return f"{existing}\n{new_text}"


# Label & List Normalizers

def normalize_label_list(value: Any) -> List[str]:
    """Recursively extracts clean, unique text labels from nested structures or JSON strings."""
    if value is None:
        return []

    if isinstance(value, dict):
        labels: List[str] = []
        key_targets = (
            "labels", "labels_present", "label",
            "text_labels", "annotations", "detected_labels"
        )
        for key in key_targets:
            if key in value:
                labels.extend(normalize_label_list(value[key]))
        return labels

    if isinstance(value, (list, tuple, set)):
        labels = []
        for item in value:
            labels.extend(normalize_label_list(item))
        return labels

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]

    if not isinstance(value, str):
        return []

    raw = value.strip()
    if not raw:
        return []

    if raw.startswith("["):
        try:
            decoded = json.loads(raw)
            if isinstance(decoded, list):
                return normalize_label_list(decoded)
        except (TypeError, ValueError):
            pass

    labels, seen = [], set()
    for part in re.split(r"[,;\n|]+", raw):
        label = re.sub(r"^\s*(?:[-*•]|\d+[.)]|[a-zA-Z][.)])\s*", "", part).strip()
        key = label.lower()
        if label and key not in seen:
            seen.add(key)
            labels.append(label)

    return labels


def _inline_labels(value: str) -> List[str]:
    """Parses inline label string literals or stringified lists."""
    value = (value or "").strip().rstrip(",").strip()
    if not value:
        return []

    if value.startswith("["):
        try:
            decoded = ast.literal_eval(value)
        except (SyntaxError, ValueError):
            decoded = None

        if isinstance(decoded, (list, tuple, set, str)):
            return normalize_label_list(decoded)

        labels = []
        for part in value.strip("[]").split(","):
            label = part.strip()
            if len(label) >= 2 and label[0] == label[-1] and label[0] in ('"', "'"):
                label = label[1:-1]
            labels.extend(normalize_label_list(label))
        return labels

    return normalize_label_list(value.strip("[]"))


# Formula & Chemical SMILES Normalizers

def normalize_formula_list(value: Any) -> List[str]:
    """Extracts unique LaTeX math formulas or equations from strings/lists/dicts."""
    if isinstance(value, dict):
        for field in ("latex_formulas", "latex", "formulas", "equations"):
            if field in value:
                return normalize_formula_list(value[field])
        return []

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    return normalize_formula_list(decoded)
            except (TypeError, ValueError):
                pass
        parts = [p for p in re.split(r"[\n]+", raw) if p.strip()]
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        return []

    formulas, seen = [], set()
    for part in parts:
        text = _as_text(part)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            formulas.append(text)
    return formulas


def normalize_smiles(value: Any) -> List[str]:
    """Extracts unique chemical SMILES strings from input payloads."""
    if isinstance(value, dict):
        for field in ("smiles", "smiles_strings", "chemical_structures", "structures"):
            if field in value:
                return normalize_smiles(value[field])
        return []

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                decoded = json.loads(raw)
                if isinstance(decoded, list):
                    return normalize_smiles(decoded)
            except (TypeError, ValueError):
                pass
        parts = re.split(r"[\n;,]+", raw)
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        return []

    smiles, seen = [], set()
    for part in parts:
        if isinstance(part, dict):
            part = part.get("smiles") or part.get("smiles_string") or part.get("string") or ""
        text = _as_text(part)
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            smiles.append(text)
    return smiles


# VLM Payload & Question Parsing

def _item_text(item: Any) -> str:
    """Extracts string content from raw dictionary item fields."""
    if isinstance(item, str):
        return item.strip()
    if not isinstance(item, dict):
        return str(item).strip() if item is not None else ""

    text_fields = ("extracted_text", "text", "answer", "student_answer", "content", "value")
    for field in text_fields:
        value = item.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list)):
            return str(value).strip()
    return ""


def _item_key(item: Any) -> Optional[Any]:
    """Extracts question identifier keys from payload dictionaries."""
    if not isinstance(item, dict):
        return None

    key_fields = (
        "question_number", "question_id", "question_no",
        "question", "number", "id", "label", "key"
    )
    for field in key_fields:
        value = item.get(field)
        if value is not None and not isinstance(value, (dict, list)):
            return value
    return None


def _json_objects_from_text(text: str) -> List[Any]:
    """Scans and parses multiple JSON objects embedded within raw text blocks."""
    decoder = json.JSONDecoder()
    objects, index = [], 0
    while index < len(text):
        candidates = [
            pos for pos in (text.find("{", index), text.find("[", index))
            if pos != -1
        ]
        if not candidates:
            break
        start = min(candidates)
        try:
            obj, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        objects.append(obj)
        index = end
    return objects


def parse_question_headers(text: str) -> List[Dict[str, Any]]:
    """Identifies question header numbers and pattern positions in text."""
    headers = []
    patterns = [
        (r"Q\s*(\d+)\s*:?", "question"),
        (r"Question\s*(\d+)\s*:?", "question"),
        (r"^\s*(\d+)\s*[\.\)\]]", "numbered"),
        (r"([a-zA-Z])\s*\)", "letter"),
    ]
    for pattern, header_type in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE):
            headers.append({
                "type": header_type,
                "match": match.group(0),
                "number": match.group(1) if match.groups() else None,
                "position": match.start(),
                "full_match": match.group(0),
            })
    headers.sort(key=lambda item: item["position"])
    return headers


def _answers_from_payload(payload: Any) -> Dict[str, str]:
    """Extracts and maps question answer blocks from raw JSON payload structures."""
    from .core import _extract_answer_items

    result, last_qid = {}, None
    for index, item in enumerate(_extract_answer_items(payload)):
        text = _item_text(item)
        if not text:
            continue
        raw_key = _item_key(item)
        qid = normalize_question_key(raw_key) if raw_key is not None else ""

        if re.fullmatch(r"Q\d+", qid):
            result[qid] = _merge_blocks(result.get(qid, ""), text)
            last_qid = qid
        elif last_qid:
            result[last_qid] = _merge_blocks(result[last_qid], text)
        elif qid:
            fallback_qid = f"Q{index + 1}"
            result[fallback_qid] = _merge_blocks(result.get(fallback_qid, ""), text)
            last_qid = fallback_qid

    return {qid: text for qid, text in result.items() if text}


def parse_vlm_json_output(vlm_response_text: str) -> Dict[str, str]:
    """Parses raw VLM text output into structured question-to-answer mappings."""
    if not vlm_response_text:
        return {}

    raw = str(vlm_response_text).strip()
    if not raw:
        return {}

    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE).strip()

    # 1. Attempt direct JSON parsing
    for candidate in (raw, cleaned):
        try:
            return _answers_from_payload(json.loads(candidate))
        except json.JSONDecodeError:
            continue

    # 2. Attempt parsing embedded JSON objects
    objects = _json_objects_from_text(cleaned)
    if objects:
        merged = {}
        for obj in objects:
            for qid, text in _answers_from_payload(obj).items():
                merged[qid] = _merge_blocks(merged.get(qid, ""), text)
        if merged:
            return merged

    # 3. Fallback to document regex block extractor
    return document_parser.extract_question_blocks(cleaned)