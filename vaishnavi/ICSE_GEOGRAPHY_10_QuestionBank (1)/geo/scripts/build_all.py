"""Build geography_questions.csv + geography_questions_with_images.xlsx (same layout as the Maths / Civics banks)."""
import csv, io, math, shutil
from pathlib import Path
from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.hyperlink import Hyperlink
from PIL import Image
from data_2025 import P25
from data_2026 import P26
from data_2024 import P24

BASE = Path(__file__).resolve().parent.parent
DIAG = BASE / "diagrams"
SRC = {"trees25":"G25_trees","winds25":"G25_winds_AB","dam25":"G25_dam","glass26":"G26_glass","rain26":"G26_rainwater",
       "hirakud26":"G26_hirakud","solar26":"G26_solar","landfill26":"G26_landfill","rain24":"G24_rainwater","bins24":"G24_bins",
       "map":"G_map_G43S10","india":"G_india_outline"}
SCORE = {"recall":1,"knowledge":1,"understanding":1,"application":2,"analysis":3,"evaluate":3}

def diff_from_marks(m): return "Easy" if m == 1 else ("Medium" if m <= 3 else "Hard")
def diff_from_tag(tag):
    s = [SCORE[w] for w in tag.lower().replace("&"," ").replace(","," ").split() if w in SCORE]
    a = sum(s)/len(s)
    return "Easy" if a < 1.5 else ("Medium" if a < 2.5 else "Hard")

rows, first_use = [], {}
n = 0
for paper, data in ((1, P25), (2, P26), (3, P24)):
    for r in data:
        n += 1
        qid = f"Q{n:03d}"
        q, sub, marks, chap, text, img = r[:6]
        tag = r[6].strip() if len(r) > 6 else ""
        if tag: diff, basis = diff_from_tag(tag), "CISCE competency tag"
        else:   diff, basis = diff_from_marks(marks), "estimated from marks"
        if img and img not in first_use: first_use[img] = qid
        review = ""
        if paper == 3 and q == 1: review = "Map sheet G43S7 is not in the PDF - map image not available"
        if paper == 3 and q == 2: review = "2024 outline map not in the PDF - generic India outline attached"
        if paper == 1 and q == 2: review = "Outline map not in the 2025 PDF - generic India outline attached"
        rows.append(dict(question_id=qid, paper_no=paper, question_number=q, sub_part=sub, marks=marks, chapter=chap,
                         difficulty=diff, difficulty_basis=basis, question_text=text, has_diagram="Yes" if img else "No",
                         diagram_image=f"diagrams/{first_use[img]}.png" if img else "", needs_review=review, _img=img))

# final picture files named after the first question that uses them (shared pictures stored once)

cols = ["question_id","paper_no","question_number","sub_part","marks","chapter","difficulty","difficulty_basis",
        "question_text","has_diagram","diagram_image","needs_review"]
with open(BASE / "geography_questions.csv", "w", newline="", encoding="utf-8-sig") as fh:
    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore"); w.writeheader(); w.writerows(rows)

# ---------------- Excel ----------------
BIG = {"map": (400, 540), "india": (430, 440)}
SMALL = (330, 230)
HEADER_FILL = PatternFill("solid", fgColor="1F3864"); YES_FILL = PatternFill("solid", fgColor="E2EFDA"); REVIEW_FILL = PatternFill("solid", fgColor="FFF2CC")
WIDTHS = {"open_diagram":16,"question_id":10,"paper_no":9,"question_number":10,"sub_part":8,"marks":7,"chapter":32,"difficulty":11,"difficulty_basis":22,"question_text":100,"has_diagram":11,"diagram_image":22,"needs_review":40}
TEXT_WIDTH = 100
xcols = []
for c in cols:
    xcols += ["diagram", "diagram_2", "open_diagram", "diagram_image"] if c == "diagram_image" else [c]
wb = Workbook(); ws = wb.active; ws.title = "Question Bank"; ws.append(xcols)
for cell in ws[1]:
    cell.font = Font(bold=True, color="FFFFFF"); cell.fill = HEADER_FILL
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
ci = {c: i+1 for i, c in enumerate(xcols)}
for r, row in enumerate(rows, start=2):
    for c in xcols:
        if c in ("diagram", "diagram_2", "open_diagram"): continue
        cell = ws.cell(row=r, column=ci[c], value=row[c])
        cell.alignment = Alignment(vertical="top", wrap_text=(c in ("question_text","needs_review")))
    h = 0
    if row["_img"]:
        size = BIG.get(row["_img"], SMALL)
        img = Image.open(DIAG / f"{first_use[row['_img']]}.png").convert("RGB"); img.thumbnail(size); img = img.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
        buf = io.BytesIO(); img.save(buf, "PNG", optimize=True); buf.seek(0)
        ws.add_image(XLImage(buf), f"{get_column_letter(ci['diagram'])}{r}")
        h = img.height
        ws.cell(row=r, column=ci["has_diagram"]).fill = YES_FILL
        sheet = "D_" + first_use[row["_img"]]
        link_font = Font(color="0563C1", underline="single", bold=True)
        c1 = ws.cell(row=r, column=ci["open_diagram"], value="Open diagram (full size)")
        c1.hyperlink = Hyperlink(ref=c1.coordinate, location=f"'{sheet}'!A1", display=c1.value); c1.font = link_font
        c1.alignment = Alignment(vertical="top", wrap_text=True)
    lines = math.ceil(len(row["question_text"]) / (TEXT_WIDTH * 1.05)) + 1
    ws.row_dimensions[r].height = min(409, max(h * 0.75 + 6, lines * 15))
    if row["needs_review"]: ws.cell(row=r, column=ci["needs_review"]).fill = REVIEW_FILL
for c, i in ci.items():
    ws.column_dimensions[get_column_letter(i)].width = 58 if c == "diagram" else (50 if c == "diagram_2" else WIDTHS.get(c, 14))
ws.column_dimensions[get_column_letter(ci["diagram_2"])].hidden = True
ws.freeze_panes = "B2"; ws.auto_filter.ref = ws.dimensions
# one full-size sheet per picture, opened by the "Open diagram" links
for k, qid in first_use.items():
    d = wb.create_sheet("D_" + qid); d.sheet_view.showGridLines = False
    back = d["A1"]; back.value = "<< Back to Question Bank (click)"; back.font = Font(color="0563C1", underline="single", bold=True, size=12)
    back.hyperlink = Hyperlink(ref="A1", location="'Question Bank'!A1", display=back.value)
    d["A2"] = f"Diagram used by {qid}" + (" and other questions" if sum(1 for r in rows if r["_img"] == k) > 1 else ""); d["A2"].font = Font(bold=True)
    im = Image.open(DIAG / f"{qid}.png").convert("RGB"); im.thumbnail((1250, 1700)); im = im.quantize(colors=256, method=Image.Quantize.MEDIANCUT)
    b = io.BytesIO(); im.save(b, "PNG", optimize=True); b.seek(0)
    d.add_image(XLImage(b), "A4"); d.sheet_view.zoomScale = 100
wb.save(BASE / "geography_questions_with_images.xlsx")
print(len(rows), "rows;", sum(1 for r in rows if r["_img"]), "with diagrams;", len(first_use), "picture files")
