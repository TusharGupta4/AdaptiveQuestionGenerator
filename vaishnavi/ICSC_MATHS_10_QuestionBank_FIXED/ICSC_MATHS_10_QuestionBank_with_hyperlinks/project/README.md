# ICSE Maths Class-10 — Mock Test Question Bank (v2: cropped diagrams)

Turns the ICSE sample-paper PDFs into a structured question bank for a mock-test app:

`question | marks | chapter | difficulty | image (only if the question has one)`

## What was wrong in v1 and what changed

| Problem in v1 | Fix in v2 |
|---|---|
| **Diagram column pointed to the WHOLE PDF page** (2–3 diagrams + other questions on it) | Each figure is now cropped on its own (`diagrams/Q006.png`), tight, with the watermark removed |
| Wrong page for some rows (2026 prints sub-questions out of order, so Q044's figure was linked to the wrong page) | Ownership now comes from the position on the page (reading order), not from text order |
| Diagram flag came from keywords: "significant **figures**" counted as a diagram, while graphs, tables and bills were missed | `has_diagram` is decided from the PDF's actual drawings. 26 rows now have images (graphs, tables, bills, figures) |
| Diagram letters leaked into the question text (`... P B D C A E 100 m 14 35`) | Text inside a figure box is dropped (the image carries it) |
| Page headers glued into text (`Solved Paper - 2025 2`, `T26 511 – SPECIMEN 3 of 13`) | Stripped |
| `chapter` and `difficulty` were dropped | Added back (see below) |
| Hard to find mistakes | New `pdf_page` and `needs_review` columns |

Question splitting (82 rows) and marks are unchanged from v1.

## Files

- `mathematics_questions.csv` — final question bank (UTF-8 with BOM, opens fine in Excel)
- `mathematics_questions_with_images.xlsx`: same data with every picture/diagram **embedded in the row** (columns `diagram`, `diagram_2`). No hyperlinks, so no Excel security prompt, and it works on its own, even straight from the zip.
- `diagrams/` — 27 cropped PNGs (`Q036_1/_2` = a question with two figures)
- `pdfs/` source papers, `scripts/` pipeline

## Columns

| Column | Meaning |
|---|---|
| `question_id` | Unique id (Q001...) |
| `paper_no` | 1 = 2025 paper, 2 = 2026 specimen paper |
| `question_number`, `sub_part` | e.g. 5 and `iii` |
| `marks` | Marks for that row |
| `chapter` | ICSE chapter (keyword rules + a few manual corrections) |
| `difficulty` | Easy / Medium / Hard |
| `difficulty_basis` | `CISCE competency tag` (2026) or `estimated from marks` (2025) |
| `question_text` | Question with its options |
| `has_diagram` | Yes / No |
| `diagram_image` | Path to the crop (comma-separated if two) |
| `pdf_page` | PDF page where the question is printed, to cross-check against the source |
| `needs_review` | `Yes` when extraction garbled the maths symbols |

## Difficulty, how it is set

- **2026 paper:** CISCE prints a tag like `[Application & Evaluation]` after each question.
  Knowledge/Understanding = 1, Application = 2, Analysis/Evaluation = 3, averaged:
  below 1.5 Easy, below 2.5 Medium, otherwise Hard. The tag is removed from `question_text`.
- **2025 paper:** the PDF has no tags, so it is **estimated from marks** (1 = Easy, 2-3 = Medium, 4+ = Hard).
  Treat both as a first pass that a teacher can overwrite.

## Run it again

```bash
pip install pymupdf openpyxl pillow
python scripts/run_pipeline.py
```

| Step | Script | Output |
|---|---|---|
| 1 | `extract_text.py` | PDF text (watermark removed, figure text dropped) |
| 2 | `clean_questions.py` | Cleaned text |
| 3 | `prepare_questions.py` | Rows split by Question / (i) / (ii) with marks |
| 4 | `render_diagrams.py` (uses `diagram_finder.py`) | Cropped diagrams, `has_diagram`, `diagram_image`, `pdf_page` |
| 5 | `enrich_questions.py` | chapter, difficulty, needs_review, final CSV |
| 6 | `build_excel.py` | The Excel file |

How a diagram is found: vector drawings and pictures on each page are merged into figures, nearby
labels (A, B, 60°, 25 cm, axis numbers) are added, then each figure is given to the most recent
`(i)`/`(ii)` marker before it while reading the page left column → right column → next page.

## Known limitations

- **Maths formulas in `question_text` are still rough.** Fractions, matrices and exponents are
  flattened by PDF text extraction (`5 4` for 5/4), and the 2026 PDF's maths font extracts as junk.
  The 9 worst rows have `needs_review = Yes`, but other rows with formulas can be flattened too.
  Use `pdf_page` to compare. Proper fix: a maths-aware OCR (e.g. Mathpix) or showing a cropped image of the question.
- Questions that say "use a graph paper" / "draw the diagram" have no figure in the paper,
  so `has_diagram = No` (the student draws it).
- Chapters and 2025 difficulty are automatic; spot-check before using in tests.
- New paper with a different layout: add it to `PAPER_LAYOUT` in `diagram_finder.py`
  (two-column or not, header height) and check the crops.
