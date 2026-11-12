# ICSE Geography (H.C.G. Paper 2) Class-10: Mock Test Question Bank

Separate bank, same columns as Maths and Civics:
`question_id | paper_no | question_number | sub_part | marks | chapter | difficulty | difficulty_basis | question_text | has_diagram | diagram_image | needs_review`

Sources (in `pdfs/`): `paper_no` 1 = ICSE 2025 (Oswaal solved), 2 = ICSE 2026 specimen (CISCE), 3 = ICSE 2024 (Oswaal solved).
183 rows (61 per paper, each paper = 80 marks).

## Files
- `geography_questions.csv`: the bank (UTF-8 with BOM)
- `geography_questions_with_images.xlsx`: same data, diagram **embedded in the row** (`diagram`), plus an `open_diagram` link that jumps to a full-size sheet (`D_Q###`, with a Back link).
- `diagrams/Q###.png`: full-size pictures, named after the first question that uses them (shared pictures stored once).

## Diagrams (12 pictures, 50 rows)
- Survey of India map sheet G43S10 (full page incl. legend): all 2025 and 2026 Q1 rows.
- Blank outline map of India (from the 2026 paper): every Q2 row in all three papers.
- 2025: tree-layers picture (Q3 iii), wind Figures A and B (Q4 iii), hydel dam (Q8 iv).
- 2026: broken glass (Q3 x), rainwater harvesting (Q7 iv), Hirakud dam (Q8 ii), solar panels (Q8 iv), landfill (Q12 ii).
- 2024: rainwater harvesting (Q7 iv), waste bins (Q12 i).

## Difficulty
2026: CISCE tag (Recall/Understanding = 1, Application = 2, Analysis/Evaluate = 3, averaged). 2025 and 2024: estimated from marks (1 = Easy, 2-3 = Medium). Teachers can overwrite.

## Known issues
- **2024 Q1 (map sheet G43S7) has no map**: that sheet is not in the PDF. Flagged in `needs_review`.
- The 2024 and 2025 PDFs do not include their outline map, so the 2026 blank India outline is attached (flagged for 2024/2025 Q2).
- Climate tables are typed into `question_text` as `Month: ... | Temp: ... | Rainfall: ...`.
- No answers column (the PDFs contain solutions, not extracted).
- Chapters are my assignment, spot-check before use.

## Run again
`pip install openpyxl pillow` then `python scripts/build_all.py`
