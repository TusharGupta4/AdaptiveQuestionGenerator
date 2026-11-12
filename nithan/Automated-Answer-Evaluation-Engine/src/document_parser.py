"""Full-document question parsing helpers.

The parser in this module deliberately operates on the complete assembled
answer-sheet transcript, never on individual PDF pages.  Question blocks are
therefore allowed to span any number of page boundaries.
"""

import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


_QUESTION_HEADER_RE = re.compile(
    r'(?im)^[ \t]*(?:question|ques|q)[ \t]*[.\-:_]?[ \t]*'
    r'(?:no\.?|number|#)?[ \t]*[.\-:_]?[ \t]*(\d{1,3})\b[ \t]*[.:)\]\-]?'
)
_ANSWER_HEADER_RE = re.compile(
    r'(?im)^[ \t]*(?:ans(?:wer)?)[ \t]*[.\-:_]?[ \t]*'
    r'(?:no\.?|number|#)?[ \t]*[.\-:_]?[ \t]*(\d{1,3})\b[ \t]*[.:)\]\-]?'
)
_BARE_HEADER_RE = re.compile(
    r'(?m)^[ \t]*\(?(\d{1,3})\)?[ \t]*[.)\]]\s*(?=\S)'
)


def normalize_question_key(key) -> str:
    """Normalize labels like '1)', 'Question 1', 'q1', '1.' to canonical 'Q1'."""
    if key is None:
        return ''
    if isinstance(key, (int, float)) and not isinstance(key, bool):
        return f"Q{int(key)}"

    value = str(key).strip()
    if not value:
        return ''

    match = re.search(r'(?i)\bq(?:uestion)?\s*[_\-:#.)\]\s]*(\d+)\b', value)
    if not match:
        match = re.search(r'\b(\d+)\b', value)
    if match:
        return f"Q{int(match.group(1))}"

    return value.upper()


def _header_matches(text: str, pattern: re.Pattern) -> List[Dict]:
    matches = []
    seen_starts = set()
    for match in pattern.finditer(text):
        start = match.start()
        if start in seen_starts:
            continue
        seen_starts.add(start)
        matches.append({
            'question_id': f"Q{int(match.group(1))}",
            'number': int(match.group(1)),
            'start': start,
            'end': match.end(),
            'header': match.group(0).strip(),
        })
    return matches


def _sequential_headers(headers: List[Dict]) -> List[Dict]:
    """Keep only bare numbered headers that form a 1, 2, 3... sequence."""
    selected = []
    expected = 1
    for header in headers:
        number = header['number']
        if number == expected:
            selected.append(header)
            expected += 1
    return selected


def _find_question_headers(text: str) -> List[Dict]:
    headers = _header_matches(text, _QUESTION_HEADER_RE)
    if headers:
        return headers

    headers = _header_matches(text, _ANSWER_HEADER_RE)
    if headers:
        return headers

    return _sequential_headers(_header_matches(text, _BARE_HEADER_RE))


def _merge_block(existing: str, new_text: str) -> str:
    existing = (existing or '').strip()
    new_text = (new_text or '').strip()
    if not existing:
        return new_text
    if not new_text:
        return existing
    return f"{existing}\n{new_text}"


def extract_question_blocks(full_text: str,
                            expected_ids: Optional[Iterable[str]] = None) -> Dict[str, str]:
    """
    Split the complete document transcript into question answer blocks.

    Every block starts immediately after a question header and ends immediately
    before the next question header.  Because the input is the already assembled
    multi-page document, a block naturally contains text from all pages between
    the two headers.

    ``expected_ids`` is accepted for API compatibility and as a hint for callers;
    missing tags are not guessed here.  Callers can use
    :func:`rubric_evaluator.match_questions_to_blocks` to perform semantic
    fallback matching for missing tags.
    """
    if not full_text or not str(full_text).strip():
        return {}

    text = str(full_text)
    headers = _find_question_headers(text)
    if not headers:
        return {}

    blocks: Dict[str, str] = {}
    for index, header in enumerate(headers):
        start = header['end']
        end = headers[index + 1]['start'] if index + 1 < len(headers) else len(text)
        block = text[start:end].strip()
        block = re.sub(r'^[ \t]*[:\-–—]+[ \t]*', '', block, count=1).strip()
        if not block:
            continue
        qid = header['question_id']
        blocks[qid] = _merge_block(blocks.get(qid, ''), block)

    return blocks


def parse_full_document_questions(full_text: str,
                                  expected_ids: Optional[Iterable[str]] = None,
                                  vlm_parser=None) -> Dict[str, str]:
    """
    Parse the full assembled answer sheet into ``{"Q1": "...", ...}``.

    If a ``vlm_parser`` callable is supplied it is attempted first; when it
    returns no usable blocks the deterministic full-document regex parser is
    used as a fallback.
    """
    expected = [
        normalize_question_key(qid)
        for qid in (expected_ids or [])
        if normalize_question_key(qid)
    ]

    parsed: Dict[str, str] = {}
    if vlm_parser is not None:
        try:
            candidate = vlm_parser(full_text, expected)
        except TypeError:
            candidate = vlm_parser(full_text)
        except Exception:
            candidate = None
        if isinstance(candidate, dict):
            for key, value in candidate.items():
                qid = normalize_question_key(key)
                if not qid or not isinstance(value, str) or not value.strip():
                    continue
                parsed[qid] = _merge_block(parsed.get(qid, ''), value)

    fallback = extract_question_blocks(full_text, expected)
    for qid, block in fallback.items():
        if qid not in parsed or not parsed[qid].strip():
            parsed[qid] = block

    return parsed


parse_question_blocks = extract_question_blocks
parse_document_questions = parse_full_document_questions
split_into_question_blocks = extract_question_blocks
