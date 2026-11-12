"""
STEP : build the Excel version with the pictures EMBEDDED in the sheet
--------------------------------------------------------------------
mathematics_questions_with_images.xlsx
  One row per question, same columns as the CSV.  Each question that has a
  picture/diagram shows it right inside the row (columns `diagram` and
  `diagram_2`), so there are no hyperlinks, no security prompt, and the file
  works on its own (even straight from a zip) without the diagrams folder.
  The CSV still lists the image file paths in `diagram_image`.
"""

import csv
import io
import math
from pathlib import Path

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "mathematics_questions.csv"
XLSX_PATH = BASE_DIR / "mathematics_questions_with_images.xlsx"

THUMB = (330, 230)            # max picture size in pixels inside the sheet
PIC_COL_WIDTH = 50            # Excel column width that fits a 330px picture
TEXT_WIDTH = 90
WIDTHS = {"question_id": 10, "paper_no": 9, "question_number": 10, "sub_part": 8,
          "marks": 7, "chapter": 28, "difficulty": 11, "difficulty_basis": 22,
          "question_text": TEXT_WIDTH, "has_diagram": 11, "diagram_image": 22,
          "pdf_page": 9, "needs_review": 14}
HEADER_FILL = PatternFill("solid", fgColor="1F3864")
YES_FILL = PatternFill("solid", fgColor="E2EFDA")
REVIEW_FILL = PatternFill("solid", fgColor="FFF2CC")


def thumbnail(path):
    img = Image.open(BASE_DIR / path).convert("RGB")
    img.thumbnail(THUMB)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return XLImage(buf), img.height


def main():
    with open(CSV_PATH, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))

    columns = []
    for c in rows[0].keys():
        if c == "diagram_image":
            columns += ["diagram", "diagram_2", "diagram_image"]
        else:
            columns.append(c)

    wb = Workbook()
    ws = wb.active
    ws.title = "Question Bank"
    ws.append(columns)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    col_idx = {c: i + 1 for i, c in enumerate(columns)}
    for r, row in enumerate(rows, start=2):
        paths = [p for p in row["diagram_image"].split(",") if p]
        for c in columns:
            if c in ("diagram", "diagram_2"):
                continue
            value = row[c]
            if c in ("paper_no", "question_number", "marks", "pdf_page") and str(value).isdigit():
                value = int(value)
            cell = ws.cell(row=r, column=col_idx[c], value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=(c in ("question_text", "needs_review")))

        # pictures, embedded in the row
        heights = []
        for slot, path in zip(("diagram", "diagram_2"), paths[:2]):
            xl, h = thumbnail(path)
            ws.add_image(xl, f"{get_column_letter(col_idx[slot])}{r}")
            heights.append(h)
        if paths:
            ws.cell(row=r, column=col_idx["has_diagram"]).fill = YES_FILL
            text_lines = math.ceil(len(row["question_text"]) / (TEXT_WIDTH * 1.05)) + 1
            ws.row_dimensions[r].height = max(max(heights) * 0.75 + 6, text_lines * 15)
        if row["needs_review"]:
            ws.cell(row=r, column=col_idx["needs_review"]).fill = REVIEW_FILL

    for c, i in col_idx.items():
        w = PIC_COL_WIDTH if c in ("diagram", "diagram_2") else WIDTHS.get(c, 14)
        ws.column_dimensions[get_column_letter(i)].width = w
    # hide the 2nd picture column when no row needs it
    if not any(len([p for p in r["diagram_image"].split(",") if p]) > 1 for r in rows):
        ws.column_dimensions[get_column_letter(col_idx["diagram_2"])].hidden = True
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = ws.dimensions

    wb.save(XLSX_PATH)
    n = sum(len([p for p in r["diagram_image"].split(",") if p][:2]) for r in rows)
    print(f"Excel written: {XLSX_PATH.name}  ({len(rows)} rows, {n} picture(s) embedded)")


if __name__ == "__main__":
    main()
