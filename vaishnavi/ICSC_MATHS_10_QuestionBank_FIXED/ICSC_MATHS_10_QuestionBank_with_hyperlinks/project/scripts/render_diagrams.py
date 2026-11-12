"""
STEP 4 : crop every diagram and link it into the CSV
--------------------------------------------------------------------
OLD behaviour : saved the whole PDF page for any question containing the word
                "diagram" -> student saw a full page of unrelated questions.
NEW behaviour : finds each figure's exact bounding box (see diagram_finder.py),
                saves ONLY that figure as a tight, watermark-free PNG, and
                gives it to the correct sub-question.

  * diagrams/Q006.png            one figure for row Q006
  * diagrams/Q027_1.png, _2.png  when one sub-question has several figures
                                  (e.g. Figure 1 / Figure 2 far apart)
  * has_diagram / diagram_image are decided from the PDF geometry, not from
    keywords, so graphs, tables and bills are caught and "significant figures"
    no longer triggers a false positive.
"""

import csv
import re
import sys
from pathlib import Path

import pymupdf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagram_finder as df  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent.parent
PDF_FOLDER = BASE_DIR / "pdfs"
DIAGRAMS_FOLDER = BASE_DIR / "diagrams"
CSV_PATH = BASE_DIR / "cleaned_questions" / "mathematics_questions.csv"

ZOOM = 3.0      # ~216 dpi: sharp text and thin lines inside the crop
STACK_GAP = 45  # pt: figures of one sub-question closer than this become ONE image

# Columns only needed by the pipeline itself; not wanted in the final CSV.
INTERNAL_ONLY_COLUMNS = {"source", "section", "question_total_marks", "pages"}

PAPER_LAYOUT = df.PAPER_LAYOUT
# Wording that normally means "a picture should exist here" -> used ONLY to warn
HINT_RE = re.compile(r"given (diagram|figure|graph|bill)|figure given|diagram given|"
                     r"refer to the given|study the graph|given table|"
                     r"following table|frequency distribution", re.I)


def group_figures(figs):
    """Merge figures that sit right above/below each other on the same page+column."""
    figs = sorted(figs, key=lambda f: (f.page, f.col, f.rect.y0))
    groups = []
    for f in figs:
        if groups:
            g = groups[-1]
            if (g["page"], g["col"]) == (f.page, f.col) and f.rect.y0 - g["rect"].y1 < STACK_GAP:
                g["rect"] = g["rect"] | f.rect
                continue
        groups.append({"page": f.page, "col": f.col, "rect": pymupdf.Rect(f.rect)})
    return groups


def main():
    if not CSV_PATH.exists():
        print("Run prepare_questions.py first -- CSV not found.")
        return
    with open(CSV_PATH, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
        fieldnames = list(rows[0].keys()) if rows else []

    DIAGRAMS_FOLDER.mkdir(exist_ok=True)
    for old in DIAGRAMS_FOLDER.glob("*.png"):
        old.unlink()                       # drop the old whole-page images

    # --- locate figures in every paper (watermark is stripped inside locate())
    docs, found, page_of = {}, {}, {}
    for source, (two_col, header_y) in PAPER_LAYOUT.items():
        pdf = PDF_FOLDER / f"{source}.pdf"
        if not pdf.exists():
            continue
        doc = pymupdf.open(pdf)
        figures, markers = df.locate(doc, two_col, header_y)
        docs[source] = doc
        for m in markers:
            if m.owner:
                page_of.setdefault((source, m.owner), m.page)   # page where "(i)" etc. is printed
        for f in figures:
            if f.owner:
                found.setdefault((source, f.owner), []).append(f)
        print(f"{source}: {sum(1 for f in figures if f.owner)} figure(s) found")

    warnings = []
    for row in rows:
        row["diagram_image"] = ""
        row["has_diagram"] = "No"
        key = (row["source"], (int(row["question_number"]), row["sub_part"]))
        row["pdf_page"] = page_of.get(key, "")
        figs = found.get(key)
        if not figs:
            if HINT_RE.search(row["question_text"]):
                warnings.append(f'{row["question_id"]} (Q{row["question_number"]}'
                                f'({row["sub_part"]})): text mentions a figure but none found')
            continue
        groups = group_figures(figs)
        names = []
        for i, g in enumerate(groups, start=1):
            page = docs[row["source"]][g["page"] - 1]
            clip = g["rect"] & page.rect          # padding already applied by diagram_finder
            pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip)
            name = f'{row["question_id"]}.png' if len(groups) == 1 \
                else f'{row["question_id"]}_{i}.png'
            pix.save(DIAGRAMS_FOLDER / name)
            names.append(f"diagrams/{name}")
        row["has_diagram"] = "Yes"
        row["diagram_image"] = ",".join(names)

    final_fields = [f for f in fieldnames if f not in INTERNAL_ONLY_COLUMNS] + ["pdf_page"]
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=final_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: v for k, v in row.items() if k in final_fields})

    n_yes = sum(1 for r in rows if r["has_diagram"] == "Yes")
    print(f"Diagram crops saved: {len(list(DIAGRAMS_FOLDER.glob('*.png')))} image(s) "
          f"for {n_yes} row(s) -> {DIAGRAMS_FOLDER}")
    for w in warnings:
        print("  CHECK:", w)


if __name__ == "__main__":
    main()
