"""
Run the whole History & Civics question-bank pipeline.

  1. build_questions.py   PDFs         -> rows + cropped pictures/tables (diagrams/)
  2. enrich_questions.py  rows         -> chapter, difficulty, review flags, final CSV
  3. build_excel.py       CSV + images -> history_civics_questions_with_images.xlsx

Put the paper PDFs in /pdfs, then:   python scripts/run_pipeline.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for step in ("build_questions.py", "enrich_questions.py", "build_excel.py"):
    print(f"\n=== {step} ===")
    if subprocess.run([sys.executable, str(HERE / step)]).returncode != 0:
        sys.exit(f"{step} failed")
print("\nDone: history_civics_questions.csv + history_civics_questions_with_images.xlsx")
