from __future__ import annotations

import copy
import re

DEFAULT_KEYWORD_THRESHOLD = 65.0
DEFAULT_WORD_COUNT_TOLERANCE = 0.0
DEFAULT_WORD_COUNT_PENALTY_SCALE = 1.0

GRADE_PROFILES = {
    'junior': {
        'key': 'junior',
        'label': 'Junior',
        'class_band': 'Class 6-8',
        'classes': (6, 7, 8),
        'keyword_threshold': 45.0,
        'word_count_tolerance': 0.40,
        'word_count_penalty_scale': 0.75,
        'weights': {
            'semantic': 0.35,
            'fuzzy_keyword': 0.35,
            'word_count': 0.15,
            'ocr_quality': 0.15,
        },
        'formal_term_validation': False,
        'feedback_persona': (
            'You are a warm, encouraging middle-school teacher who focuses on '
            'concepts and effort. Use simple, supportive language suitable for '
            'students in Classes 6 to 8.'
        ),
        'tone_guidance': (
            'Be encouraging and concept-focused. Praise what the student '
            'understood, tolerate minor spelling or phrasing slips, and suggest '
            'one clear next step without using harsh or overly technical language.'
        ),
    },
    'secondary': {
        'key': 'secondary',
        'label': 'Secondary',
        'class_band': 'Class 9-10',
        'classes': (9, 10),
        'keyword_threshold': 60.0,
        'word_count_tolerance': 0.10,
        'word_count_penalty_scale': 1.0,
        'weights': {
            'semantic': 0.40,
            'fuzzy_keyword': 0.30,
            'word_count': 0.15,
            'ocr_quality': 0.15,
        },
        'formal_term_validation': False,
        'feedback_persona': (
            'You are a balanced school examiner giving constructive feedback to '
            'a student in Classes 9 or 10.'
        ),
        'tone_guidance': (
            'Use clear, constructive language. Explain the score, identify the '
            'main concepts present or missing, and suggest a specific improvement '
            'while maintaining a standard school-exam level of expectation.'
        ),
    },
    'senior': {
        'key': 'senior',
        'label': 'Senior / Competitive',
        'class_band': 'Class 11-12',
        'classes': (11, 12),
        'keyword_threshold': 75.0,
        'word_count_tolerance': 0.0,
        'word_count_penalty_scale': 1.35,
        'weights': {
            'semantic': 0.45,
            'fuzzy_keyword': 0.30,
            'word_count': 0.10,
            'ocr_quality': 0.15,
        },
        'formal_term_validation': True,
        'feedback_persona': (
            'You are a strict senior examiner providing academic, exam-ready '
            'feedback to a student in Classes 11 or 12'
        ),
        'tone_guidance': (
            'Use technical, formal, academic language. Demand precise terminology, '
            'exam-ready structure, and accurate use of concepts. Point out missing '
            'technical terms or weak argumentation directly but professionally.'
        ),
    },
}


def _profile_for_grade(grade: int):
    for profile in GRADE_PROFILES.values():
        if grade in profile['classes']:
            return copy.deepcopy(profile)
    return None


def resolve_grade_profile(selected_class=None):
    """Resolve a Class/Grade selection into its grade strictness profile."""
    if selected_class is None:
        return None

    text = str(selected_class).strip().lower()
    if not text:
        return None

    if 'competitive' in text:
        return copy.deepcopy(GRADE_PROFILES['senior'])

    for match in re.findall(r'\d+', text):
        grade = int(match)
        if 6 <= grade <= 12:
            return _profile_for_grade(grade)

    if 'junior' in text or 'middle' in text:
        return copy.deepcopy(GRADE_PROFILES['junior'])
    if 'secondary' in text:
        return copy.deepcopy(GRADE_PROFILES['secondary'])
    if 'senior' in text or 'higher secondary' in text:
        return copy.deepcopy(GRADE_PROFILES['senior'])

    return None


def get_grade_profile(selected_class=None):
    return resolve_grade_profile(selected_class)


def grade_band(selected_class=None):
    profile = resolve_grade_profile(selected_class)
    return profile['key'] if profile else None
