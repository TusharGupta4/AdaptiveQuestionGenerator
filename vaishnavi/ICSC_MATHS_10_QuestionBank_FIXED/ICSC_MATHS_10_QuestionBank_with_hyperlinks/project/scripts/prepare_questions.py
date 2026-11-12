r"""
STEP 3 : cleaned text -> structured CSV
--------------------------------------------------------------------
This is a full rewrite of the old line-by-line "digit + dot" parser,
which was breaking on this paper's real structure:

    Question 5                     <- MAIN question anchor (always the
                                       literal word "Question" + number)
    (i)  ..... text .....          <- SUB-QUESTION anchor (roman numeral
    [4]                               in brackets), each with its own
                                       marks tag like [4]
        (a) ..... text .....       <- these are OPTIONS / SUB-PARTS of
        (b) ..... text .....          the sub-question, NOT new questions
    (ii) ..... text .....
    [4]

The old regex `^\d+[.)]` matched ANY line starting with a bare number
+ dot/bracket -- which is exactly what measurements ("5 cm."), table
rows, and construction steps look like, so it kept creating fake rows.
It also never split the MCQ block in Question 1 at all, because
"(i)", "(a)" etc. never matched a leading digit.

Fix:
  - Anchor main questions ONLY on the literal word "Question <num>"
    (this string is printed once per question in the source PDFs).
  - Anchor sub-questions ONLY on roman numerals in parentheses -- (i),
    (ii), (iii) ... -- and only when they are the *next expected* one
    in sequence, so a stray "(x)" inside a formula can't be mistaken
    for sub-question (x).
  - Everything else (including "(a)", "(b)", "(c)", "(d)" options/
    sub-parts, and MCQ answer choices) is treated as body text that
    belongs to the CURRENT sub-question -- it is appended to
    question_text instead of becoming a new row.
  - One CSV row = one sub-question ((i), (ii), (iii)...). If a
    question has no sub-questions at all, the question itself is one
    row.
  - Marks: a bracket like "[4]" right after "Question N" is the total
    for that whole question (stored in question_total_marks). A
    bracket right after a sub-question is that sub-question's own
    marks (stored in marks). Question 1 in this paper is an MCQ block
    worth [15] total with 15 one-line sub-questions and no individual
    marks tags -- in that case the total is split evenly across the
    sub-questions when it divides evenly, otherwise it is left blank
    per-row and only recorded at the question level.
  - Diagram detection: any sub-question whose text mentions
    "diagram", "figure", or "graph paper" is flagged has_diagram=Yes,
    and the PDF page(s) it was extracted from are recorded so
    render_diagrams.py can save those pages as images and this script
    can then link them in the diagram_image column.
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CLEANED_FOLDER = BASE_DIR / "cleaned_questions"
DIAGRAMS_FOLDER = BASE_DIR / "diagrams"
OUTPUT_FILE = CLEANED_FOLDER / "mathematics_questions.csv"

INPUT_FILES = sorted(CLEANED_FOLDER.glob("*_cleaned.txt"))

DIAGRAM_KEYWORDS = ("diagram", "figure", "graph paper")

# Running header printed on many pages -- not real question content.
BOILERPLATE_SUBSTRINGS = (
    "oswaal icse question bank",
)

ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}


def roman_to_int(roman: str):
    roman = roman.lower()
    if not roman or any(ch not in ROMAN_VALUES for ch in roman):
        return None
    total = 0
    prev = 0
    for ch in reversed(roman):
        value = ROMAN_VALUES[ch]
        total += -value if value < prev else value
        prev = max(prev, value)
    return total


PAGE_RE = re.compile(r"^---\s*Page\s+(\d+)\s*---$", re.IGNORECASE)
SECTION_A_RE = re.compile(r"^SECTION[\s\-]*A\b", re.IGNORECASE)
SECTION_B_RE = re.compile(r"^SECTION[\s\-]*B\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"^Question\s+(\d{1,2})\b(.*)$", re.IGNORECASE)
ROMAN_SUBPART_RE = re.compile(r"^\(([ivxlcdm]{1,6})\)\s*(.*)$", re.IGNORECASE)
# The first MCQ option, "(a) ...". Once a sub-question's options have
# started, a lone "[n]" line stops being treated as a marks tag -- it
# is far more likely to be a 1x1 matrix answer choice like "(b) [8]"
# (this exact false positive showed up in the 2026 paper).
FIRST_OPTION_RE = re.compile(r"^\(a\)", re.IGNORECASE)
BARE_OPTION_RE = re.compile(r"\([a-e]\)", re.IGNORECASE)
MARKS_ONLY_RE = re.compile(r"^\[(\d{1,3})\]$")
# Both PDFs end with an "ANSWERS" / "DRAFT MARKING SCHEME" section that
# re-uses "Question 1", "(i)", "(ii)" ... labels for the *explanations*,
# not real questions (e.g. "(i) Option (d) is correct. Explanation:
# ..."). That must not be parsed as mock-test content, so once one of
# these headings is seen, parsing of that file stops for good.
ANSWER_KEY_HEADING_RE = re.compile(
    r"marking scheme|^ANSWERS?$", re.IGNORECASE
)
# Fallback for the rarer case where a marks tag is glued onto the end
# of a sentence instead of sitting on its own line, e.g.
# "...are 35 deg and 14 deg respectively.[5]"
INLINE_MARKS_RE = re.compile(r"\[(\d{1,3})\]")


def is_boilerplate(line: str) -> bool:
    low = line.lower()
    return any(sub in low for sub in BOILERPLATE_SUBSTRINGS)


def strip_header_footer_sandwich(lines):
    """Drop running-header lines, and the bare page-number lines that
    sandwich them (e.g. '5', 'Oswaal ICSE Question Bank...', '5')."""
    cleaned = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if is_boilerplate(line):
            if cleaned and re.fullmatch(r"\d{1,3}", cleaned[-1]):
                cleaned.pop()
            i += 1
            if i < n and re.fullmatch(r"\d{1,3}", lines[i]):
                i += 1
            continue
        cleaned.append(line)
        i += 1
    return cleaned


def has_diagram_keyword(text: str) -> bool:
    low = text.lower()
    return any(word in low for word in DIAGRAM_KEYWORDS)


# Running page headers/footers that PyMuPDF leaves glued into the text stream.
JUNK_RES = [
    re.compile(r"\s*\d{1,3}\s+Solved Paper\s*-\s*20\d\d\s+\d{1,3}\b"),   # "4 Solved Paper - 2025 4"
    re.compile(r"\s*Solved Paper\s*-\s*20\d\d\s+\d{1,3}\b"),
    re.compile(r"\s*T26 511\s*[\u2013-]\s*SPECIMEN(\s+Page\s+\d+\s+of\s+\d+|\s+\d+\s+of\s+\d+)?"),
    re.compile(r"\s*ICSE 2026 SPECIMEN\b.*$"),
    re.compile(r"[\ue000-\uf8ff]"),                                     # private-use bullets
]


def strip_junk(text: str) -> str:
    for rx in JUNK_RES:
        text = rx.sub(" ", text)
    return text


class Row:
    """One sub-question (or, if it has none, one whole question)."""

    def __init__(self, paper_no, source, section, question_number,
                 question_total_marks, sub_part, sub_part_index, start_page):
        self.paper_no = paper_no
        self.source = source
        self.section = section
        self.question_number = question_number
        self.question_total_marks = question_total_marks
        self.sub_part = sub_part
        self.sub_part_index = sub_part_index
        self.start_page = start_page
        self.end_page = start_page
        self.marks = None
        self.text_parts = []

    def add_text(self, text, page, check_inline_marks=True):
        if text:
            if check_inline_marks and self.marks is None:
                m = INLINE_MARKS_RE.search(text)
                if m:
                    self.marks = int(m.group(1))
                    text = (text[:m.start()] + text[m.end():]).strip()
            if text:
                self.text_parts.append(text)
        self.end_page = max(self.end_page, page)

    def finalize(self, question_id):
        text = " ".join(strip_junk(" ".join(self.text_parts)).split())
        pages = (f"{self.start_page}"
                 if self.start_page == self.end_page
                 else f"{self.start_page}-{self.end_page}")
        diagram = has_diagram_keyword(text)
        return {
            "question_id": question_id,
            "source": self.source,
            "paper_no": self.paper_no,
            "section": self.section or "",
            "question_number": self.question_number,
            "sub_part": self.sub_part or "",
            "marks": self.marks if self.marks is not None else "",
            "question_total_marks": (self.question_total_marks
                                      if self.question_total_marks is not None
                                      else ""),
            "question_text": text,
            "pages": pages,
            "has_diagram": "Yes" if diagram else "No",
            "diagram_image": "",  # filled in later by link_diagram_images.py
            "chapter": "Not assigned",
            "difficulty": "Not assigned",
        }


def parse_file(path: Path, source: str, paper_no_start: int):
    raw_lines = path.read_text(encoding="utf-8").splitlines()
    lines = strip_header_footer_sandwich(raw_lines)

    rows = []
    current_page = 1
    section = ""
    paper_no = paper_no_start
    seen_section_a = False
    seen_section_b_since_a = False

    question_number = None
    question_total_marks = None
    seen_romans_for_question = set()

    current_row = None
    # text seen after "Question N" but before its first "(i)" sub-part
    question_preamble = []
    # Was the PREVIOUS line just a bare option marker like "(b)" on its
    # own? If so, a "[n]" on the current line is that option's VALUE
    # (e.g. a 1x1 matrix answer choice "(b)\n[8]"), never marks.
    prev_line_was_bare_option = False

    def flush_row():
        nonlocal current_row
        if current_row is not None:
            rows.append(current_row)
            current_row = None

    for line in lines:
        this_line_is_bare_option = bool(BARE_OPTION_RE.fullmatch(line))

        if ANSWER_KEY_HEADING_RE.search(line):
            # Everything after this is the answers / marking scheme,
            # not real question content -- stop parsing this file.
            break

        page_match = PAGE_RE.match(line)
        if page_match:
            current_page = int(page_match.group(1))
            prev_line_was_bare_option = this_line_is_bare_option
            continue

        if SECTION_A_RE.match(line):
            if seen_section_a and seen_section_b_since_a:
                paper_no += 1
            seen_section_a = True
            seen_section_b_since_a = False
            section = "Section A"
            prev_line_was_bare_option = this_line_is_bare_option
            continue

        if SECTION_B_RE.match(line):
            section = "Section B"
            seen_section_b_since_a = True
            prev_line_was_bare_option = this_line_is_bare_option
            continue

        q_match = QUESTION_RE.match(line)
        if q_match:
            flush_row()
            question_number = int(q_match.group(1))
            question_total_marks = None
            seen_romans_for_question = set()
            question_preamble = []
            trailing = q_match.group(2).strip()
            if trailing:
                question_preamble.append(trailing)
            prev_line_was_bare_option = this_line_is_bare_option
            continue

        # A standalone "[n]" bracket seen any time before the first
        # sub-question of this question is its total marks (e.g. the
        # 15-item MCQ block's "[15]"). It doesn't always sit on the
        # line right after "Question N" -- some papers put a couple of
        # instruction lines in between -- so this is checked for as
        # long as we're still in the preamble, not just on the very
        # next line.
        if (question_number is not None and current_row is None
                and question_total_marks is None):
            m = MARKS_ONLY_RE.match(line)
            if m:
                question_total_marks = int(m.group(1))
                prev_line_was_bare_option = this_line_is_bare_option
                continue

        if question_number is not None:
            sub_match = ROMAN_SUBPART_RE.match(line)
            if sub_match:
                candidate = roman_to_int(sub_match.group(1))
                # Accept any not-yet-used roman numeral in a sane range
                # (1-20) as a new sub-question. We deliberately do NOT
                # require strict (i, ii, iii, ...) order any more --
                # some PDFs (multi-column page layouts) print their
                # sub-questions out of visual order in the extracted
                # text stream (e.g. i, iii, ii, iv, v ...). Rows are
                # re-sorted into proper order at the end of this
                # function. The range cap (<=20) and "not seen before"
                # check are what keep this from misfiring on options
                # like "(c)" / "(d)", since a bare "c" or "d" is also
                # technically a valid (large-valued) roman numeral.
                if (candidate is not None and 1 <= candidate <= 20
                        and candidate not in seen_romans_for_question):
                    flush_row()
                    seen_romans_for_question.add(candidate)
                    current_row = Row(
                        paper_no, source, section, question_number,
                        question_total_marks, sub_match.group(1).lower(),
                        candidate, current_page,
                    )
                    if question_preamble:
                        current_row.add_text(" ".join(question_preamble),
                                              current_page)
                        question_preamble = []
                    current_row.add_text(sub_match.group(2), current_page)
                    prev_line_was_bare_option = this_line_is_bare_option
                    continue

            # A "[n]" bracket is treated as this sub-question's marks
            # UNLESS the line right before it was a bare option marker
            # like "(b)" on its own -- that pattern means "[n]" is the
            # option's VALUE (e.g. a 1x1 matrix answer "(b)\n[8]"),
            # not a marks tag. This also correctly allows the marks
            # tag to sit AFTER the options, which some papers do.
            m = MARKS_ONLY_RE.match(line)
            if m and current_row is not None:
                if current_row.marks is None and not prev_line_was_bare_option:
                    current_row.marks = int(m.group(1))
                else:
                    # Rejected as marks (e.g. it's an option's own value
                    # like a 1x1 matrix "[8]") -- keep it as visible
                    # text, but skip inline-marks detection since we've
                    # already made the call on this exact line.
                    current_row.add_text(line, current_page,
                                          check_inline_marks=False)
                prev_line_was_bare_option = this_line_is_bare_option
                continue

            if is_boilerplate(line):
                prev_line_was_bare_option = this_line_is_bare_option
                continue

            if current_row is not None:
                current_row.add_text(line, current_page)
            else:
                question_preamble.append(line)

        prev_line_was_bare_option = this_line_is_bare_option

    flush_row()

    # Question with no sub-parts at all (defensive fallback: shouldn't
    # happen in this paper, but keeps the parser from silently
    # dropping content if a future paper is formatted differently).
    if question_number is not None and not rows and question_preamble:
        row = Row(paper_no, source, section, question_number,
                   question_total_marks, "", 0, current_page)
        row.add_text(" ".join(question_preamble), current_page)
        rows.append(row)

    # Some PDFs print sub-questions out of order in the extracted text
    # (multi-column layout), e.g. i, iii, ii, iv, v ... Put each
    # question's rows back into proper (i, ii, iii, ...) order. This
    # is a stable sort keyed by (paper_no, question_number) first, so
    # the overall document order across different questions is kept
    # exactly as parsed -- only the order *within* one question's
    # sub-parts is corrected.
    rows.sort(key=lambda r: (r.paper_no, r.question_number, r.sub_part_index))

    # Split an un-tagged total evenly across sub-questions that got no
    # individual marks tag of their own (this is exactly Question 1's
    # MCQ block: [15] total over 15 one-line sub-questions).
    by_question = {}
    for row in rows:
        by_question.setdefault((row.paper_no, row.question_number), []).append(row)

    for (_, _), group in by_question.items():
        untagged = [r for r in group if r.marks is None]
        total = group[0].question_total_marks
        if untagged and total is not None and len(untagged) == len(group) \
                and total % len(group) == 0:
            per_row = total // len(group)
            for r in untagged:
                r.marks = per_row

    return rows


def main():
    if not INPUT_FILES:
        print("No *_cleaned.txt files found in", CLEANED_FOLDER)
        return

    all_rows = []
    paper_no = 0
    for path in INPUT_FILES:
        source = path.stem.replace("_cleaned", "")
        file_rows = parse_file(path, source, paper_no_start=paper_no + 1)
        all_rows.extend(file_rows)
        paper_no = file_rows[-1].paper_no if file_rows else paper_no

    fieldnames = [
        "question_id", "source", "paper_no", "section", "question_number",
        "sub_part", "marks", "question_total_marks", "question_text",
        "pages", "has_diagram", "diagram_image", "chapter", "difficulty",
    ]

    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(all_rows, start=1):
            writer.writerow(row.finalize(question_id=f"Q{i:03d}"))

    diagram_count = sum(1 for r in all_rows if has_diagram_keyword(
        " ".join(r.text_parts)))
    print(f"CSV created: {OUTPUT_FILE}")
    print(f"Total rows: {len(all_rows)}  |  flagged with a diagram: {diagram_count}")


if __name__ == "__main__":
    main()
