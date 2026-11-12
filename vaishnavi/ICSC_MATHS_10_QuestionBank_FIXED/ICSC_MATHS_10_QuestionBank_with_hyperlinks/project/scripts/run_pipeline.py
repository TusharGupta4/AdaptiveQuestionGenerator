"""
Runs the full pipeline in order:
  1. extract_text.py     PDF          -> extracted_text/*.txt
  2. clean_questions.py  raw text     -> cleaned_questions/*_cleaned.txt
  3. prepare_questions.py cleaned text -> mathematics_questions.csv
  4. render_diagrams.py  CSV + PDFs   -> diagrams/*.png (tight crops) + CSV updated
  5. enrich_questions.py CSV          -> chapter, difficulty, review flag, final CSV
  6. build_excel.py      CSV + images -> mathematics_questions_with_images.xlsx

Usage:  python scripts/run_pipeline.py
(run from the project's root folder, or anywhere -- paths are
resolved relative to this file)
"""

import runpy
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

STEPS = [
    "extract_text.py",
    "clean_questions.py",
    "prepare_questions.py",
    "render_diagrams.py",
    "enrich_questions.py",
    "build_excel.py",
]

for step in STEPS:
    print(f"\n=== Running {step} ===")
    runpy.run_path(str(SCRIPTS_DIR / step), run_name="__main__")

print("\nPipeline finished. Final output: mathematics_questions.csv  +  mathematics_questions_with_images.xlsx")
