import csv
import os
import re
from typing import Dict, List, Optional

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEFAULT_SAMPLE_DIR = os.path.join(ROOT_DIR, 'sample_data')

CANONICAL_COLUMNS = (
    'question_no', 'question_text', 'max_marks', 'reference_answer',
    'keywords', 'subject_type', 'required_diagram_labels',
)

COLUMN_ALIASES = {
    'question_no': {'q_no', 'qno', 'q_number', 'question_no', 'question_number',
                    'question_id', 'questionno', 'q', 'no', 'number', 's_no',
                    'sr_no', 'serial_no', 'id'},
    'question_text': {'question', 'question_text', 'questiontext', 'question_prompt',
                      'question_statement', 'prompt', 'q_text', 'text'},
    'max_marks': {'marks', 'max_marks', 'maximum_marks', 'mark', 'total_marks',
                  'max_score', 'score', 'maximum_score'},
    'reference_answer': {'reference_answer', 'reference_ans', 'reference', 'answer',
                         'model_answer', 'model_ans', 'reference_answer_key',
                         'answer_key', 'expected_answer', 'ideal_answer'},
    'keywords': {'keywords', 'key_words', 'keyword', 'key_concepts', 'key_points',
                 'keypoints', 'key_terms', 'key_phrases'},
    'subject_type': {'subject_type', 'paper_type', 'paper_category', 'category',
                     'stream', 'discipline', 'question_type', 'assessment_type'},
    'required_diagram_labels': {'required_diagram_labels', 'diagram_labels',
                                'required_labels', 'diagram_required_labels',
                                'labels_required', 'diagram_label',
                                'expected_diagram_labels'},
}


def _normalize_header(name) -> str:
    if name is None:
        return ''
    value = str(name).replace('\ufeff', '').strip().lower()
    return re.sub(r'[^a-z0-9]+', '_', value).strip('_')


def _canonical_column(normalized_header: str) -> str:
    for canonical, aliases in COLUMN_ALIASES.items():
        if normalized_header in aliases:
            return canonical
    return ''


def _build_header_map(fieldnames) -> Dict[str, str]:
    header_map = {}
    for original in list(fieldnames) if fieldnames is not None else []:
        canonical = _canonical_column(_normalize_header(original))
        if canonical and canonical not in header_map:
            header_map[canonical] = original
    return header_map


def _get_cell(row: Dict, header_map: Dict[str, str], canonical: str) -> str:
    original = header_map.get(canonical)
    if not original:
        return ''
    value = row.get(original)
    return '' if value is None else str(value).strip()


def _coerce_marks(value, default: float = 5.0) -> float:
    try:
        if value is None or str(value).strip() == '':
            return default
        marks = float(value)
    except (TypeError, ValueError):
        return default
    return marks if marks > 0 else default


def normalize_question_no(value, fallback_index: Optional[int] = None) -> str:
    text = '' if value is None else str(value).strip()
    if text:
        match = re.search(r'(?i)\bq(?:uestion)?\s*[_\-:#.)\]\s]*(\d+)\b', text)
        if not match:
            match = re.search(r'\b(\d+)\b', text)
        if match:
            return f"Q{int(match.group(1))}"
        return text.upper()
    if fallback_index is not None:
        return f"Q{fallback_index}"
    return ''


def _natural_sort_key(value):
    parts = re.split(r'(\d+)', str(value))
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.lower())
        for part in parts
    )


def _resolve_child_dir(parent: Optional[str], name) -> Optional[str]:
    if not parent or not name or not os.path.isdir(parent):
        return None
    direct = os.path.join(parent, os.fspath(name))
    if os.path.isdir(direct):
        return direct
    target = os.path.basename(os.fspath(name).rstrip(os.sep)).lower()
    try:
        for entry in os.scandir(parent):
            if entry.is_dir() and entry.name.lower() == target:
                return entry.path
    except OSError:
        return None
    return None


def _has_subdirectories(folder: str) -> bool:
    try:
        return any(
            entry.is_dir() and not entry.name.startswith('.')
            for entry in os.scandir(folder)
        )
    except OSError:
        return False


def _resolve_class_dir(class_name: str, base_dir=None) -> Optional[str]:
    base = os.path.abspath(os.fspath(base_dir or DEFAULT_SAMPLE_DIR))
    return _resolve_child_dir(base, class_name)


def _resolve_subject_dir_in_class(class_name: str, subject_name: str,
                                  base_dir=None) -> Optional[str]:
    return _resolve_child_dir(_resolve_class_dir(class_name, base_dir), subject_name)


def _resolve_file_in_dir(folder: Optional[str], name,
                         default_ext: str = '') -> Optional[str]:
    if not folder or not name or not os.path.isdir(folder):
        return None
    file_name = os.fspath(name).strip()
    if not file_name:
        return None
    if default_ext and not file_name.lower().endswith(default_ext.lower()):
        file_name = f'{file_name}{default_ext}'
    direct = os.path.join(folder, file_name)
    if os.path.isfile(direct):
        return direct
    target_lower = file_name.lower()
    try:
        for entry in os.scandir(folder):
            if entry.is_file() and entry.name.lower() == target_lower:
                return entry.path
    except OSError:
        return None
    return None


def _resolve_paper_path_in_class(class_name: str, subject_name: str,
                                 paper_name: str, base_dir=None) -> Optional[str]:
    folder = _resolve_subject_dir_in_class(class_name, subject_name, base_dir)
    return _resolve_file_in_dir(folder, paper_name, '.csv')


def _resolve_subject_dir(subject: str, base_dir=None) -> Optional[str]:
    base = os.path.abspath(os.fspath(base_dir or DEFAULT_SAMPLE_DIR))
    return _resolve_child_dir(base, subject)


def _has_csv_files(folder: str) -> bool:
    try:
        return any(
            entry.is_file() and entry.name.lower().endswith('.csv')
            for entry in os.scandir(folder)
        )
    except OSError:
        return False


def _resolve_paper_path(subject: str, paper: str, base_dir=None) -> Optional[str]:
    return _resolve_file_in_dir(_resolve_subject_dir(subject, base_dir), paper, '.csv')


def _read_csv(path: str):
    last_error = None
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
        try:
            with open(path, 'r', encoding=encoding, newline='') as file:
                reader = csv.DictReader(file)
                return list(reader.fieldnames or []), list(reader)
        except UnicodeDecodeError as error:
            last_error = error
            continue
    if last_error:
        raise last_error
    return [], []


def _parse_question_rows(fieldnames, rows, subject='', paper='', source_file='',
                         class_name='') -> List[Dict]:
    header_map = _build_header_map(fieldnames)
    reference_data_available = (
        'reference_answer' in header_map and 'keywords' in header_map
    )
    questions = []
    for index, row in enumerate(rows, start=1):
        if not any(value not in (None, '') for value in row.values()):
            continue
        question_no = normalize_question_no(
            _get_cell(row, header_map, 'question_no'), fallback_index=index)
        if not question_no:
            continue
        reference_answer = _get_cell(row, header_map, 'reference_answer')
        keywords = _get_cell(row, header_map, 'keywords')
        subject_type = _get_cell(row, header_map, 'subject_type')
        required_diagram_labels = _get_cell(
            row, header_map, 'required_diagram_labels')
        if not reference_data_available:
            reference_answer = ''
            keywords = ''
        has_reference = bool(reference_answer or keywords)
        questions.append({
            'question_no': question_no,
            'question_id': question_no,
            'question_number': question_no,
            'question_text': _get_cell(row, header_map, 'question_text'),
            'max_marks': _coerce_marks(_get_cell(row, header_map, 'max_marks'), 5.0),
            'reference_answer': reference_answer,
            'reference_ans': reference_answer,
            'keywords': keywords,
            'key_words': keywords,
            'subject_type': subject_type,
            'required_diagram_labels': required_diagram_labels,
            'required_diagram_label_list': [
                label.strip()
                for label in re.split(r'[,;\n|]+', required_diagram_labels)
                if label.strip()
            ],
            'has_reference': has_reference,
            'scoring_mode': 'rubric' if has_reference else 'zero_shot_llm',
            'class_name': class_name,
            'class': class_name,
            'subject': subject,
            'paper': paper,
            'source_file': source_file,
        })
    return questions
