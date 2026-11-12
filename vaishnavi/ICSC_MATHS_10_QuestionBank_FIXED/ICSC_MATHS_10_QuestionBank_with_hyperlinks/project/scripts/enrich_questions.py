"""
STEP 5 : add chapter, difficulty and a review flag
--------------------------------------------------------------------
The brief for the mock-test question bank is:
    question | marks | chapter | difficulty | image (if the question has one)
The earlier version dropped chapter + difficulty.  They are filled in here.

chapter     ICSE Class-10 chapter, chosen by keyword rules (CHAPTER_RULES, first
            match wins).  A few rows are too flattened/garbled by PDF text
            extraction for any keyword to hit (matrices, the garbled 2026
            trig assertion, ...) -- those are in CHAPTER_OVERRIDES.  If a new
            paper gives "Unclassified", add a rule or an override line.

difficulty  2026 paper : CISCE prints a competency tag after every question,
                         e.g. [Application & Evaluation].  It is converted
                         with a simple score (Knowledge/Understanding = 1,
                         Application = 2, Analysis/Evaluation = 3, averaged):
                              < 1.5 Easy | < 2.5 Medium | otherwise Hard
            2025 paper : no tags in the PDF, so it is ESTIMATED from marks
                         (1 = Easy, 2-3 = Medium, 4+ = Hard).
            `difficulty_basis` says which of the two was used for each row.
            Treat both as a starting point a teacher can overwrite.

needs_review  "Yes" when text extraction turned maths symbols into junk
              (e.g. sin -> 𝑠𝑠𝑠, matrices -> ቂ ቃ).  Compare with pdf_page.
"""

import csv
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "cleaned_questions" / "mathematics_questions.csv"
ROOT_COPY = BASE_DIR / "mathematics_questions.csv"

FINAL_COLUMNS = [
    "question_id", "paper_no", "question_number", "sub_part", "marks",
    "chapter", "difficulty", "difficulty_basis", "question_text",
    "has_diagram", "diagram_image", "pdf_page", "needs_review",
]

# --------------------------------------------------------------- chapters
# (chapter, regex) -- checked top to bottom, first match wins.
CHAPTER_RULES = [
    ("Banking (Recurring Deposit)", r"recurring deposit"),
    ("Shares and Dividends", r"dividend|\bshares?\b"),
    ("GST", r"\b[cs]?i?gst\b|\bbill\b"),
    ("Probability", r"probability|at random|marble|\bcards?\b"),
    ("Linear Inequations", r"inequation|solution set|real number line"),
    ("Mensuration", r"volume|surface area|spher|cylind|\bcone\b|hemisphere|capsule|melted"),
    ("Statistics", r"\bmean\b|\bmedian\b|\bmode\b|frequency|histogram|ogive|quartile"),
    ("Trigonometry",
     r"(?:sin|cos|tan|cot|sec|cosec)(?=[\s\d\u03b8A-Z])|angles? of (?:depression|elevation)|trigonometr"),
    ("Coordinate Geometry",
     r"reflect|x\s?-\s?axis|y[\s-]*axis|origin|coordinates|centroid|equation of|"
     r"line passing|equally inclined|intercepts|divides the line"),
    ("Loci and Constructions", r"\bconstruct|ruler and compass|locus|loci"),
    ("Circles", r"tangent|chord|\bcircle\b|circumference"),
    ("Similarity", r"similar|[~\u223c]|scale factor"),
    ("Quadratic Equations", r"quadratic|\broots?\b|consecutive"),
    ("Factorisation of Polynomials", r"factor|polynomial|remainder"),
    ("Matrices", r"matri[xc]"),
    ("Geometric Progression", r"geometric progression|\bg\.?p\.?\b"),
    ("Arithmetic Progression", r"progression|\ba\.?p\.?\b"),
    ("Ratio and Proportion", r"proportion|\bratio\b"),
]

# (paper_no, question_number, sub_part) -> chapter, for rows keywords cannot reach
CHAPTER_OVERRIDES = {
    (1, 1, "v"): "Matrices",                       # "If A = [0 1; 1 0] then A^2" (flattened)
    (1, 1, "ix"): "Loci and Constructions",        # circumcentre / incentre statements
    (1, 3, "ii"): "Matrices",                      # A, B, C matrices, find A + C ...
    (1, 8, "iii"): "Quadratic Equations",          # speed/time word problem
    (2, 1, "iii"): "Similarity",                   # shaded area via ΔAPQ ~ ΔABC
    (2, 1, "v"): "Trigonometry",                   # sec/tan assertion (garbled text)
    (2, 1, "x"): "Ratio and Proportion",           # paint mixture table
    (2, 3, "iii"): "Loci and Constructions",       # ruler-and-compass, equidistant loci
}

# -------------------------------------------------------------- difficulty
TAG_RE = re.compile(
    r"\[\s*(?:(?:Knowledge|Understanding|Application|Analysis|Analyze|Evaluation|Evaluate)"
    r"\s*(?:,|&|and)?\s*)+\]", re.IGNORECASE)
TAG_SCORES = {"knowledge": 1, "understanding": 1, "application": 2,
              "analysis": 3, "analyze": 3, "evaluation": 3, "evaluate": 3}

# garbled-symbol ranges that PDF text extraction produces for maths fonts
GARBLE_RE = re.compile("[\U0001D400-\U0001D7FF\u1200-\u139f\ue000-\uf8ff]")


def classify_chapter(paper, q, sub, text):
    key = (int(paper), int(q), sub)
    if key in CHAPTER_OVERRIDES:
        return CHAPTER_OVERRIDES[key]
    for chapter, pattern in CHAPTER_RULES:
        if re.search(pattern, text, re.IGNORECASE if chapter != "Trigonometry" else 0):
            return chapter
    return "Unclassified"


def difficulty_from_tag(tag):
    scores = [TAG_SCORES[w.lower()] for w in re.findall(r"[A-Za-z]+", tag)
              if w.lower() in TAG_SCORES]
    if not scores:
        return None
    avg = sum(scores) / len(scores)
    return "Easy" if avg < 1.5 else "Medium" if avg < 2.5 else "Hard"


def difficulty_from_marks(marks):
    try:
        m = int(marks)
    except (TypeError, ValueError):
        return "Medium"
    return "Easy" if m <= 1 else "Medium" if m <= 3 else "Hard"


def main():
    with open(CSV_PATH, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    unclassified = []
    for row in rows:
        text = row["question_text"]

        tag_match = TAG_RE.search(text)
        tag = tag_match.group(0) if tag_match else ""
        if tag:
            text = " ".join(TAG_RE.sub(" ", text).split())      # tag is not part of the question
        difficulty = difficulty_from_tag(tag) if tag else None
        if difficulty:
            row["difficulty"], row["difficulty_basis"] = difficulty, "CISCE competency tag"
        else:
            row["difficulty"] = difficulty_from_marks(row["marks"])
            row["difficulty_basis"] = "estimated from marks"

        row["question_text"] = text
        row["chapter"] = classify_chapter(row["paper_no"], row["question_number"],
                                          row["sub_part"], text)
        if row["chapter"] == "Unclassified":
            unclassified.append(row["question_id"])
        row["needs_review"] = "Yes" if GARBLE_RE.search(text) else ""

    for path in (CSV_PATH, ROOT_COPY):
        with open(path, "w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=FINAL_COLUMNS)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in FINAL_COLUMNS})

    print(f"CSV finalised: {ROOT_COPY}  ({len(rows)} rows)")
    print("Unclassified chapters:", ", ".join(unclassified) if unclassified else "none")
    print("Flagged needs_review:", sum(1 for r in rows if r["needs_review"]))


if __name__ == "__main__":
    main()
