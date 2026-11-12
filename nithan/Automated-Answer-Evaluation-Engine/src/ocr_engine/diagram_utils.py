import json
import re
from typing import Any, Dict, List, Optional, Tuple

from .formatters import _as_text, _inline_labels, normalize_label_list


# ---------------------------------------------------------------------------
# Diagram Normalization
# ---------------------------------------------------------------------------

def normalize_diagrams(value: Any) -> List[Dict[str, Any]]:
    """Normalizes raw VLM payloads, stringified JSON, or dict lists into standard diagram dicts."""
    if isinstance(value, dict):
        for field in ('diagrams', 'figures', 'visuals', 'detected_diagrams'):
            if field in value:
                return normalize_diagrams(value[field])
        value = [value]

    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            return normalize_diagrams(json.loads(raw))
        except (TypeError, ValueError):
            return [{
                'figure_id': '',
                'description': raw,
                'labels': [],
                'labels_present': [],
                'spatial_arrangement': '',
                'relationships': [],
            }]

    if not isinstance(value, (list, tuple)):
        return []

    diagrams = []
    for index, item in enumerate(value):
        if isinstance(item, str):
            description = item.strip()
            if description:
                diagrams.append({
                    'figure_id': f'Figure {index + 1}',
                    'description': description,
                    'labels': [],
                    'labels_present': [],
                    'spatial_arrangement': '',
                    'relationships': [],
                })
            continue

        if not isinstance(item, dict):
            continue

        labels = normalize_label_list(
            item.get('labels')
            or item.get('labels_present')
            or item.get('label')
            or item.get('text_labels')
            or item.get('annotations')
            or item.get('detected_labels')
        )
        description = _as_text(
            item.get('description')
            or item.get('caption')
            or item.get('summary')
            or item.get('content')
        )
        spatial = _as_text(
            item.get('spatial_arrangement')
            or item.get('spatial_relationship')
            or item.get('arrangement')
            or item.get('layout')
            or item.get('positioning')
        )
        relationships = normalize_label_list(
            item.get('relationships')
            or item.get('connections')
            or item.get('arrows')
        )
        figure_id = _as_text(
            item.get('figure_id')
            or item.get('id')
            or item.get('figure')
            or item.get('name')
            or item.get('title')
        )

        if not any((description, labels, spatial, relationships, figure_id)):
            continue

        diagrams.append({
            'figure_id': figure_id or f'Figure {index + 1}',
            'description': description,
            'labels': labels,
            'labels_present': labels,
            'spatial_arrangement': spatial,
            'relationships': relationships,
        })

    return diagrams


# ---------------------------------------------------------------------------
# Inline Diagram Parsing
# ---------------------------------------------------------------------------

def _inline_diagram_blocks(text: str) -> List[str]:
    """Extracts raw [DIAGRAM_PRESENT: ...] string blocks handling nested brackets."""
    if not isinstance(text, str) or not text:
        return []

    blocks = []
    lower = text.lower()
    token = '[diagram_present:'
    position = 0

    while True:
        start = lower.find(token, position)
        if start == -1:
            break
        depth = 0
        end = None
        for index in range(start, len(text)):
            character = text[index]
            if character == '[':
                depth += 1
            elif character == ']':
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end is None:
            break
        blocks.append(text[start:end + 1])
        position = end + 1

    return blocks


def _strip_inline_value(value: str) -> str:
    """Strips quotes and trailing commas from inline parameter values."""
    value = (value or '').strip().rstrip(',').strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return value.strip()


def parse_inline_diagrams(text: str) -> List[Dict[str, Any]]:
    """Parses text containing [DIAGRAM_PRESENT: ...] tags into structured diagram dicts."""
    diagrams = []
    for block in _inline_diagram_blocks(text):
        content = re.sub(
            r'^\s*\[?\s*DIAGRAM_PRESENT\s*:\s*', '', block, flags=re.IGNORECASE
        )
        content = content.rstrip(']').strip()
        fields = {}

        field_pattern = re.compile(
            r'\b(Title|Figure(?:\s*_?\s*ID)?|Labels|Description|'
            r'Spatial(?:\s*_?\s*Arrangement)?|Layout|Relationships?)\s*=',
            re.IGNORECASE,
        )
        matches = list(field_pattern.finditer(content))
        for index, match in enumerate(matches):
            value_start = match.end()
            value_end = matches[index + 1].start() if index + 1 < len(matches) else len(content)
            key = re.sub(r'[^a-z]', '', match.group(1).lower())
            fields[key] = content[value_start:value_end].strip()

        title = _strip_inline_value(
            fields.get('title') or fields.get('figure') or fields.get('figureid') or ''
        )
        labels = _inline_labels(fields.get('labels', ''))
        description = _strip_inline_value(fields.get('description', ''))
        spatial = _strip_inline_value(
            fields.get('spatialarrangement')
            or fields.get('spatial')
            or fields.get('layout')
            or ''
        )
        relationships = _inline_labels(
            fields.get('relationships') or fields.get('relationship') or ''
        )

        if not any((title, labels, description, spatial, relationships)):
            continue

        diagrams.append({
            'figure_id': title or f'Figure {len(diagrams) + 1}',
            'description': description,
            'labels': labels,
            'labels_present': labels,
            'spatial_arrangement': spatial,
            'relationships': relationships,
        })

    return diagrams


# ---------------------------------------------------------------------------
# Merging & Signature Deduplication
# ---------------------------------------------------------------------------

def _diagram_signature(diagram: Dict[str, Any]) -> Tuple[str, str, Tuple[str, ...]]:
    """Generates a hashable comparison tuple for deduplicating diagram records."""
    figure_id = str(diagram.get('figure_id') or '').strip().lower()
    description = str(diagram.get('description') or '').strip().lower()[:120]
    labels = tuple(
        label.strip().lower()
        for label in normalize_label_list(diagram.get('labels'))
        if label.strip()
    )
    return figure_id, description, labels


def merge_diagram_lists(primary: Any, secondary: Any) -> List[Dict[str, Any]]:
    """Merges diagram records from JSON and inline markers without duplicates."""
    merged = normalize_diagrams(primary)
    signatures = {_diagram_signature(diagram) for diagram in merged}

    for diagram in normalize_diagrams(secondary):
        signature = _diagram_signature(diagram)
        if signature in signatures:
            continue

        duplicate = None
        labels = set(signature[2])
        for existing in merged:
            existing_signature = _diagram_signature(existing)
            if signature[0] and signature[0] == existing_signature[0]:
                duplicate = existing
                break
            existing_labels = set(existing_signature[2])
            if labels and existing_labels and len(labels & existing_labels) >= max(1, len(labels) // 2):
                duplicate = existing
                break

        if duplicate is None:
            merged.append(diagram)
            signatures.add(signature)
            continue

        for field in ('figure_id', 'description', 'spatial_arrangement'):
            if not duplicate.get(field) and diagram.get(field):
                duplicate[field] = diagram[field]

        combined_labels = normalize_label_list(
            list(duplicate.get('labels') or []) + list(diagram.get('labels') or [])
        )
        duplicate['labels'] = combined_labels
        duplicate['labels_present'] = combined_labels

        combined_relationships = normalize_label_list(
            list(duplicate.get('relationships') or [])
            + list(diagram.get('relationships') or [])
        )
        duplicate['relationships'] = combined_relationships
        signatures.add(_diagram_signature(duplicate))

    return merged


# ---------------------------------------------------------------------------
# Marker Formatting & Extraction
# ---------------------------------------------------------------------------

def _quote_diagram_value(value: Any) -> str:
    """Escapes quotes for inline marker string formatting."""
    return "'" + str(value or '').replace('\\', '\\\\').replace("'", "\\'") + "'"


def format_diagram_marker(diagram: Dict[str, Any]) -> str:
    """Renders one diagram record as an inline [DIAGRAM_PRESENT: ...] string marker."""
    diagram = diagram or {}
    title = diagram.get('figure_id') or diagram.get('title') or 'Detected diagram'
    labels = normalize_label_list(diagram.get('labels'))
    description = diagram.get('description') or ''
    spatial = diagram.get('spatial_arrangement') or ''

    parts = [
        f"Title={_quote_diagram_value(title)}",
        "Labels=[" + ', '.join(_quote_diagram_value(label) for label in labels) + "]",
    ]
    if description:
        parts.append(f"Description={_quote_diagram_value(description)}")
    if spatial:
        parts.append(f"SpatialArrangement={_quote_diagram_value(spatial)}")

    return "[DIAGRAM_PRESENT: " + ', '.join(parts) + "]"


def _append_missing_diagram_markers(body: str, diagrams: List[Dict[str, Any]]) -> str:
    """Appends DIAGRAM_PRESENT markers to document text if missing."""
    body = (body or '').rstrip()
    if not diagrams or '[DIAGRAM_PRESENT' in body.upper():
        return body

    markers = [
        marker for marker in (format_diagram_marker(diagram) for diagram in diagrams)
        if marker
    ]
    if not markers:
        return body

    return (body + '\n\n' if body else '') + '\n'.join(markers)


def extract_diagram_labels(diagrams: Any) -> List[str]:
    """Returns every unique text label found across a diagrams payload."""
    labels = []
    seen = set()
    for diagram in normalize_diagrams(diagrams):
        for label in normalize_label_list(diagram.get('labels')):
            key = label.lower()
            if key not in seen:
                seen.add(key)
                labels.append(label)
    return labels