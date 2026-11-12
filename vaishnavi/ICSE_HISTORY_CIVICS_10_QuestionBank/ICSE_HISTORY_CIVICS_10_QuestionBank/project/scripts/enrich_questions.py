"""
STEP 2 : add chapter, difficulty and review flags  ->  final CSV
--------------------------------------------------------------------
Columns follow the brief:  question | marks | chapter | difficulty | image (if any)

chapter     ICSE Class-10 History & Civics chapter, chosen by keyword rules
            (CHAPTER_RULES, first match wins) plus a few manual corrections
            (CHAPTER_OVERRIDES) where the question text alone does not say it,
            e.g. "Who is seen in the picture?" (the answer is in the image).
            "Unclassified" means: add a rule or an override line.

difficulty  2026 paper: CISCE prints a competency tag after most questions, e.g.
                        [Recall], [Application & Recall].  Score: Recall /
                        Knowledge / Understanding = 1, Application = 2,
                        Analysis / Evaluation = 3, averaged:
                              < 1.5 Easy | < 2.5 Medium | otherwise Hard
            2025 paper: no tags in the PDF -> ESTIMATED from marks
                        (1 = Easy, 2-3 = Medium, 4+ = Hard).
            `difficulty_basis` says which one was used.  A teacher can overwrite.

needs_review  says WHY a row should be compared with the PDF (pdf_page):
              - the marks printed for the whole question do not add up
              - the text mentions a picture but none was found
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_CSV = BASE_DIR / "cleaned_questions" / "history_civics_questions.csv"
FINAL_CSV = BASE_DIR / "history_civics_questions.csv"

FINAL_COLUMNS = [
    "question_id", "paper_no", "question_number", "sub_part", "marks",
    "chapter", "difficulty", "difficulty_basis", "question_text",
    "has_diagram", "diagram_image", "pdf_page", "needs_review",
]

# Marks every question of the ICSE History & Civics paper should add up to.
EXPECTED_TOTAL = {1: 16, 2: 14}      # everything else (Q3-Q10) = 10

# ---------------------------------------------------------------- chapters
CHAPTER_RULES = [
    ("The Non-Aligned Movement", r"non-?\s?alignment|\bNAM\b"),
    ("The United Nations",
     r"united nations|\bUNO\b|UNESCO|UNICEF|international court of justice|general assembly|"
     r"security council|\bveto\b"),
    ("The Second World War",
     r"second world war|world war ii|hitler|poland|hiroshima|nagasaki|manchuria|failure of the league"),
    ("Rise of Dictatorships", r"dictator"),
    ("The First World War",
     r"first world war|versailles|sarajevo|archduke|europe was reorgani[sz]ed|league of nations"),
    ("Forward Bloc and the INA", r"forward bloc|subhash|\bINA\b"),
    ("Independence and Partition of India", r"mountbatten|cabinet mission|interim government"),
    ("Mahatma Gandhi and the National Movement",
     r"gandhi|non-?cooperation|civil disobedience|quit india|rowlatt|jallianwala|dandi|"
     r"round table|simon commission|chauri"),
    # --- Civics: more specific bodies first
    ("The Prime Minister and the Council of Ministers",
     r"council of ministers|prime minister|union ministers|cabinet"),
    ("The High Courts and Subordinate Courts",
     r"high court|lok adalat|sessions court|district judge"),
    ("The Supreme Court",
     r"supreme court|court of record|revisory|original jurisdiction|judicial review|"
     r"advisory jurisdiction|judiciary|\bjudges\b"),
    ("The President and the Vice-President", r"vice[- ]president|impeach|president"),
    ("The Union Parliament",
     r"lok sabha|rajya sabha|parliament|speaker|question hour|quorum|no[- ]confidence|"
     r"money bill|sine die|adjournment"),
    # --- History: 1857 and the growth of nationalism
    ("The First War of Independence, 1857",
     r"1857|1856|revolt|rebellion|doctrine of lapse|subsidiary alliance|enfield|dalhousie|"
     r"wellesley|policies of expansion"),
    ("Growth of Nationalism",
     r"nationalis|congress|swadeshi|lytton|curzon|bengal|muslim league|press|tilak|"
     r"delhi durbar|phule|raja ram|naoroji|banerjee|arms act|vernacular"),
]

# (paper_no, question_number, sub_part) -> chapter
CHAPTER_OVERRIDES = {
    (1, 1, "v"): "The Union Parliament",                  # adjournment motion (option mentions President)
    (2, 1, "i"): "The Union Parliament",                  # exclusive powers of the Rajya Sabha
    (2, 1, "ii"): "The Union Parliament",                 # constitutional amendment headline
    (2, 1, "xiv"): "The United Nations",                  # cartoon of the 5 veto powers
    (2, 2, "v"): "Growth of Nationalism",                 # picture of Bal Gangadhar Tilak
    (1, 1, "iii"): "The Supreme Court",                   # option text mentions "High Court"
    (1, 3, "*"): "The Union Parliament",                  # lead-in says "comprises the President and ..."
    (2, 1, "xv"): "Growth of Nationalism",                # "First President of Congress" is not Civics
    (2, 2, "ii"): "The President and the Vice-President", # powers of the President (mentions SC judges)
    (2, 7, "i"): "Growth of Nationalism",                 # "first President of the Congress"
}

# -------------------------------------------------------------- difficulty
TAG_SCORES = {"recall": 1, "knowledge": 1, "understanding": 1,
              "application": 2, "analysis": 3, "analyze": 3, "analyse": 3,
              "evaluation": 3, "evaluate": 3}
PICTURE_WORDS_RE = re.compile(
    r"\b(this|given|above|following) (picture|cartoon|headline|image|photograph)\b|"
    r"\b(picture|cartoon|headline) (given|above|below)\b|\bpicture seen\b|given table|"
    r"details of (a )?few|Given below are details", re.IGNORECASE)


def classify_chapter(paper, q, sub, text):
    key = (int(paper), int(q), sub)
    if key in CHAPTER_OVERRIDES:
        return CHAPTER_OVERRIDES[key]
    if (int(paper), int(q), "*") in CHAPTER_OVERRIDES:          # whole question
        return CHAPTER_OVERRIDES[(int(paper), int(q), "*")]
    for chapter, pattern in CHAPTER_RULES:
        if re.search(pattern, text, re.IGNORECASE):
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
    m = float(marks)
    return "Easy" if m <= 1 else "Medium" if m <= 3 else "Hard"


def main():
    with open(RAW_CSV, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    totals = defaultdict(float)
    for r in rows:
        totals[(r["paper_no"], r["question_number"])] += float(r["marks"] or 0)

    unclassified, flagged = [], 0
    for r in rows:
        tag = r.pop("competency_tag", "")
        d = difficulty_from_tag(tag) if tag else None
        if d:
            r["difficulty"], r["difficulty_basis"] = d, "CISCE competency tag"
        else:
            r["difficulty"], r["difficulty_basis"] = difficulty_from_marks(r["marks"]), "estimated from marks"

        r["chapter"] = classify_chapter(r["paper_no"], r["question_number"], r["sub_part"], r["question_text"])
        if r["chapter"] == "Unclassified":
            unclassified.append(r["question_id"])

        notes = []
        expected = EXPECTED_TOTAL.get(int(r["question_number"]), 10)
        got = totals[(r["paper_no"], r["question_number"])]
        if abs(got - expected) > 0.01:
            notes.append(f"marks printed for Q{r['question_number']} add up to {got:g}, expected {expected}")
        if r["has_diagram"] == "No" and PICTURE_WORDS_RE.search(r["question_text"]):
            notes.append("text mentions a picture/table but none was found")
        r["needs_review"] = "; ".join(notes)
        flagged += bool(notes)
        if r["marks"] and float(r["marks"]) == int(float(r["marks"])):
            r["marks"] = int(float(r["marks"]))

    with open(FINAL_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=FINAL_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in FINAL_COLUMNS})

    print(f"CSV finalised: {FINAL_CSV.name}  ({len(rows)} rows)")
    print("Unclassified chapters:", ", ".join(unclassified) or "none")
    print("Rows flagged needs_review:", flagged)


if __name__ == "__main__":
    main()
