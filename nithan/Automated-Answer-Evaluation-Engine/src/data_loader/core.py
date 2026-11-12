import os
from typing import Dict, List, Optional

import pandas as pd

from .parsers import (
    CANONICAL_COLUMNS,
    DEFAULT_SAMPLE_DIR,
    _build_header_map,
    _has_csv_files,
    _has_subdirectories,
    _natural_sort_key,
    _parse_question_rows,
    _read_csv,
    _resolve_class_dir,
    _resolve_paper_path,
    _resolve_paper_path_in_class,
    _resolve_subject_dir,
    _resolve_subject_dir_in_class,
    normalize_question_no,
)

ALL_QUESTIONS = 'All Questions'


def get_subjects(base_dir=None) -> List[str]:
    """Return every subject folder under sample_data that contains at least one CSV."""
    base = os.path.abspath(os.fspath(base_dir or DEFAULT_SAMPLE_DIR))
    if not os.path.isdir(base):
        return []
    subjects = [
        entry.name for entry in os.scandir(base)
        if entry.is_dir() and not entry.name.startswith('.')
        and _has_csv_files(entry.path)
    ]
    return sorted(subjects, key=str.lower)


def get_papers(subject: str, base_dir=None) -> List[str]:
    """Return the CSV paper names inside a subject folder (case-insensitive)."""
    folder = _resolve_subject_dir(subject, base_dir)
    if not folder:
        return []
    papers = [
        os.path.splitext(entry.name)[0] for entry in os.scandir(folder)
        if entry.is_file() and not entry.name.startswith('.')
        and entry.name.lower().endswith('.csv')
    ]
    return sorted(papers, key=str.lower)


def get_available_classes(base_dir=None) -> List[str]:
    """Return top-level Class/Grade folders under sample_data."""
    base = os.path.abspath(os.fspath(base_dir or DEFAULT_SAMPLE_DIR))
    if not os.path.isdir(base):
        return []
    try:
        entries = list(os.scandir(base))
    except OSError:
        return []
    classes = []
    for entry in entries:
        if not entry.is_dir() or entry.name.startswith('.'):
            continue
        if _has_csv_files(entry.path) and not _has_subdirectories(entry.path):
            continue
        classes.append(entry.name)
    return sorted(classes, key=_natural_sort_key)


def get_available_subjects(class_name: str, base_dir=None) -> List[str]:
    """Return subject folders that contain at least one CSV paper."""
    folder = _resolve_class_dir(class_name, base_dir)
    if not folder:
        return []
    subjects = []
    try:
        for entry in os.scandir(folder):
            if (entry.is_dir() and not entry.name.startswith('.')
                    and _has_csv_files(entry.path)):
                subjects.append(entry.name)
    except OSError:
        return []
    return sorted(subjects, key=_natural_sort_key)


def get_available_papers(class_name: str, subject_name: str,
                         base_dir=None) -> List[str]:
    """Return CSV paper names inside Class/Subject without extensions."""
    folder = _resolve_subject_dir_in_class(class_name, subject_name, base_dir)
    if not folder:
        return []
    papers = []
    try:
        for entry in os.scandir(folder):
            if (entry.is_file() and not entry.name.startswith('.')
                    and entry.name.lower().endswith('.csv')):
                papers.append(os.path.splitext(entry.name)[0])
    except OSError:
        return []
    return sorted(papers, key=_natural_sort_key)


def load_paper_csv(class_name: str, subject_name: str, paper_name: str,
                   base_dir=None) -> pd.DataFrame:
    """Load a Class/Subject/Paper CSV into a DataFrame with canonical columns."""
    empty = pd.DataFrame(columns=list(CANONICAL_COLUMNS))
    path = _resolve_paper_path_in_class(
        class_name, subject_name, paper_name, base_dir)
    if not path:
        return empty
    frame = None
    last_error = None
    for encoding in ('utf-8-sig', 'utf-8', 'cp1252', 'latin-1'):
        try:
            frame = pd.read_csv(path, encoding=encoding)
            break
        except UnicodeDecodeError as error:
            last_error = error
            continue
        except pd.errors.EmptyDataError:
            return empty
        except Exception as error:
            last_error = error
            break
    if frame is None:
        if last_error:
            raise last_error
        return empty
    header_map = _build_header_map(frame.columns)
    rename_map = {
        original: canonical for canonical, original in header_map.items()
        if original in frame.columns
    }
    if rename_map:
        frame = frame.rename(columns=rename_map)
    for column in CANONICAL_COLUMNS:
        if column not in frame.columns:
            frame[column] = ''
    unnamed = [
        column for column in frame.columns if str(column).startswith('Unnamed:')
    ]
    if unnamed:
        frame = frame.drop(columns=unnamed)
    ordered = list(CANONICAL_COLUMNS) + [
        column for column in frame.columns if column not in CANONICAL_COLUMNS
    ]
    return frame[ordered].dropna(how='all').reset_index(drop=True)


def load_paper_questions(class_name: str, subject_name: str, paper_name: str,
                         base_dir=None) -> List[Dict]:
    """Load one Class/Subject/Paper CSV into normalized question dictionaries."""
    path = _resolve_paper_path_in_class(
        class_name, subject_name, paper_name, base_dir)
    if not path:
        return []
    fieldnames, rows = _read_csv(path)
    return _parse_question_rows(
        fieldnames, rows, subject=subject_name, paper=paper_name,
        source_file=path, class_name=class_name)


def load_questions_csv(csv_path, subject='', paper='') -> List[Dict]:
    """Load a single CSV file directly while normalizing flexible headers."""
    path = os.path.abspath(os.fspath(csv_path))
    if not os.path.isfile(path):
        return []
    fieldnames, rows = _read_csv(path)
    return _parse_question_rows(
        fieldnames, rows, subject=subject,
        paper=paper or os.path.splitext(os.path.basename(path))[0],
        source_file=path)


def load_paper(subject: str, paper: str, base_dir=None) -> List[Dict]:
    """Load one paper and normalize flexible headers into a stable question schema."""
    path = _resolve_paper_path(subject, paper, base_dir)
    if not path:
        return []
    fieldnames, rows = _read_csv(path)
    return _parse_question_rows(
        fieldnames, rows, subject=subject, paper=paper, source_file=path)


def format_question_option(question_no: str, question_text: str,
                           limit: int = 100) -> str:
    text = ' '.join(str(question_text or 'Untitled question').split())
    if len(text) > limit:
        text = text[:limit - 3].rstrip() + '...'
    return f"{question_no}: {text}"


def get_question_options(first, second, third=None, base_dir=None) -> List[str]:
    """Return ['All Questions', 'Q1: ...', 'Q2: ...'] for the selected paper."""
    if third is None:
        questions = load_paper(first, second, base_dir=base_dir)
    elif os.path.isdir(os.fspath(third)):
        questions = load_paper(first, second, base_dir=third)
    else:
        questions = load_paper_questions(first, second, third, base_dir=base_dir)
    return [ALL_QUESTIONS] + [
        format_question_option(question['question_no'], question.get('question_text'))
        for question in questions
    ]


def get_question(subject: str, paper: str, question_no,
                 base_dir=None) -> Optional[Dict]:
    """Look up a question by canonical id, raw id, or formatted option label."""
    target = normalize_question_no(question_no)
    if not target and isinstance(question_no, str):
        target = question_no.split(':', 1)[0].strip().upper()
    for question in load_paper(subject, paper, base_dir):
        if question['question_no'].upper() == target.upper():
            return question
    return None


def load_question_papers(base_dir=None) -> Dict[str, Dict[str, List[Dict]]]:
    """Load every subject -> paper -> normalized question records."""
    result = {}
    for subject in get_subjects(base_dir):
        result[subject] = {}
        for paper in get_papers(subject, base_dir):
            result[subject][paper] = load_paper(subject, paper, base_dir)
    return result


def load_questions(subject_or_path, paper=None, base_dir=None) -> List[Dict]:
    """Flexible loader: accept (subject, paper) or a direct CSV path."""
    if paper is None:
        path = os.path.abspath(os.fspath(subject_or_path))
        return load_questions_csv(path) if os.path.isfile(path) else []
    return load_paper(subject_or_path, paper, base_dir)
