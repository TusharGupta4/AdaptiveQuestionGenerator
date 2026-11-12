# ICSE History & Civics Class-10: Mock Test Question Bank

A **separate** bank from Maths (own CSV, Excel and pictures folder). Same columns:

`question | marks | chapter | difficulty | image (only if the question has one)`

Source papers (in `pdfs/`): ICSE 2025 solved paper (Oswaal) and the ICSE 2026 CISCE specimen paper.
`paper_no` 1 = 2025, 2 = 2026. 94 rows (47 per paper).

## Why OCR is not needed here

Both PDFs have a real text layer, so text is read directly from the PDF and is exact. The pipeline
uses page geometry (where each line, marks and picture sits), not image-to-text.

## Files

- `history_civics_questions.csv`: the question bank (UTF-8 with BOM, opens in Excel)
- `history_civics_questions_with_images.xlsx`: same data with every picture/diagram **embedded in the row** (columns `diagram`, `diagram_2`). No hyperlinks, so no Excel security prompt, and it works on its own, even straight from the zip.
- `diagrams/`: 13 cropped pictures/tables (cartoons, newspaper clippings, portraits, tables)
- `scripts/`, `pdfs/`

## Columns

| Column | Meaning |
|---|---|
| `question_id` | Q001... |
| `paper_no`, `question_number`, `sub_part` | e.g. 1, 8, `iii` |
| `marks` | Marks printed for that part |
| `chapter` | ICSE History & Civics chapter (see below) |
| `difficulty`, `difficulty_basis` | Easy / Medium / Hard and how it was decided |
| `question_text` | Question with its options |
| `has_diagram`, `diagram_image` | Yes/No and the picture path(s) |
| `pdf_page` | PDF page where the question is printed |
| `needs_review` | Empty, or the reason to compare with the PDF |

## How rows are built

- **Lead-in text is repeated in every part.** "Read the excerpt/passage..." and the intro line under
  "Question 3" are copied into each of (i), (ii), (iii), so each row stands alone.
- **MCQ instruction dropped.** "Choose the correct answers... Do not copy the question" is removed from Q1 rows.
- **Pictures printed under "Question N" before (i)** (2025 Q8, 2026 Q9) are attached to every part
  and stored once (`Q039.png` is used by Q039, Q040, Q041).
- **Text inside a picture/table box is dropped** (e.g. the age table in Q1(ii)); the image has it.
- **Marks and the 2026 tags like `[Recall]` sit in a right margin**, so they are matched to rows by position.
- **Headers/footers removed:** page numbers, "Oswaal ICSE Question Bank...", "T26 501 - SPECIMEN", "Visit CollegeDekho".

## Difficulty

- **2026:** CISCE's tag converted: Recall/Knowledge/Understanding = 1, Application = 2,
  Analysis/Evaluation = 3, averaged (below 1.5 Easy, below 2.5 Medium, else Hard).
- **2025 (and the one untagged 2026 row, Q058):** estimated from marks (1 = Easy, 2-3 = Medium, 4+ = Hard).
- A starting point; a teacher can overwrite it. `difficulty_basis` says which was used.

## Chapters

Rules + a few manual corrections in `scripts/enrich_questions.py`: Union Parliament; President and
Vice-President; Prime Minister and Council of Ministers; Supreme Court; High Courts and Subordinate
Courts; First War of Independence 1857; Growth of Nationalism; Mahatma Gandhi and the National Movement;
Forward Bloc and the INA; Independence and Partition of India; First World War; Rise of Dictatorships;
Second World War; United Nations; Non-Aligned Movement. Spot-check before use.

## Known issues

- **2025 Q8 marks:** the PDF prints [3] [3] [3] = 9, but a question should total 10. Kept as printed and
  flagged in `needs_review` (Q039-Q041). Likely a typo in the book; (iii) is probably 4.
- **No answers column.** The PDFs contain answer keys/marking schemes but they are not extracted.
- Italic/underline formatting in the question is lost (e.g. the underlined word in 2026 Q1(v)).
- Pictures include only the image, not the caption (e.g. "Tears of Blood..." stays in the text).

## Run again

```bash
pip install pymupdf openpyxl pillow
python scripts/run_pipeline.py
```
