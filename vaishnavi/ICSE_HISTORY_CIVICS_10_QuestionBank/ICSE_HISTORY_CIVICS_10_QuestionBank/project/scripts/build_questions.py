"""
STEP 1 : question-paper PDFs  ->  one row per sub-question  +  cropped pictures
--------------------------------------------------------------------------------
Everything is read from the PDF's own page geometry, no OCR.  Both papers have a
real text layer, so text is exact (OCR was what gave the poor accuracy).

How a row is built
  * "Question N" and "(i)", "(ii)" ... at the left edge start a new row.
  * Marks "[3]" and (2026 paper) competency tags "[Recall]" are printed in a
    right-hand margin, often NOT next to their question in the text stream.
    Here they are matched by position, so each lands on the right row.
  * Lead-in text under "Question N" (passage, "Read the excerpt ...") is copied
    into every part of that question, because (i), (ii), (iii) need it.
  * Pictures (cartoons, newspaper clippings, portraits) and tables are cropped
    on their own (diagrams/Q0xx.png).  A picture printed under "Question N"
    before "(i)" is shared by all parts of that question.
  * Text that sits inside a picture/table box is dropped (the image carries it).
  * Running headers/footers, page numbers, "Visit CollegeDekho" are removed.
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
RAW_CSV = BASE_DIR / "cleaned_questions" / "history_civics_questions.csv"

ZOOM = 3.0          # sharp crops (~216 dpi)
STACK_GAP = 45      # pt: pictures of one row closer than this become ONE image

# per paper: paper_no, left edge of margin zone (marks/tags), lines above/below = header/footer
PAPERS = {
    "ICSE-10 History Civics (2025)": dict(paper_no=1, margin_x=500, top=64, bottom=735),
    "ICSE-10 History Civics (2026)": dict(paper_no=2, margin_x=468, top=0, bottom=735),
}

JUNK_LINE_RE = re.compile(
    r"^(PART\s+I{1,2}\b|SECTION\s+[AB]\b|\(?Attempt\b|Visit CollegeDekho|T26 \d+\s*-\s*SPECIMEN|"
    r"SOLVED PAPER|Oswaal ICSE Question Bank|\d{1,3}$)", re.IGNORECASE)
QUESTION_LINE_RE = re.compile(r"^Question\s+\d+\s*", re.IGNORECASE)
SUBMARK_RE = re.compile(r"^\(([ivxlc]{1,6})\)\s*", re.IGNORECASE)
MARKS_RE = re.compile(r"\[\s*(\d+)\s*\]")
TAG_RE = re.compile(r"\[\s*([A-Za-z][A-Za-z &,]*?)\s*\]")


def tidy(text):
    return " ".join(text.replace("\t", " ").replace("\u00a0", " ").split())


def join_visual_lines(pieces):
    """pieces = [(page, y_center, x0, text)] -> text with side-by-side lines joined."""
    pieces = sorted(pieces, key=lambda p: (p[0], round(p[1] / 4), p[2]))
    out, cur_key, cur = [], None, []
    for page, y, x, t in pieces:
        key = (page, round(y / 4))
        if key != cur_key and cur:
            out.append(" ".join(cur))
            cur = []
        cur_key = key
        cur.append(t)
    if cur:
        out.append(" ".join(cur))
    return out


def group_figures(figs):
    figs = sorted(figs, key=lambda f: (f.page, f.col, f.rect.y0))
    groups = []
    for f in figs:
        if groups:
            g = groups[-1]
            if g["page"] == f.page and f.rect.y0 - g["rect"].y1 < STACK_GAP:
                g["rect"] = g["rect"] | f.rect
                continue
        groups.append({"page": f.page, "rect": pymupdf.Rect(f.rect)})
    return groups


def parse_paper(name, cfg, docs):
    doc = pymupdf.open(PDF_FOLDER / f"{name}.pdf")
    docs[name] = doc
    two_col, header_y = df.PAPER_LAYOUT[name]
    figures, markers = df.locate(doc, two_col, header_y)   # also strips the watermark
    last = df.find_last_page(doc)

    # ordered "start of something" events: Question N (preamble) or accepted sub-part
    events = []
    for m in markers:
        if m.kind == "Q":
            events.append((m.page, m.y, ("Q", m.value, "")))
        elif m.owner:
            events.append((m.page, m.y, ("S", m.owner[0], m.owner[1])))
    events.sort(key=lambda e: (e[0], e[1]))

    fig_boxes = [(f.page, f.rect) for f in figures if f.owner]

    text_pieces, margin_pieces = {}, {}      # key (q, roman or "") -> list
    page_of = {}
    for pi in range(last):                    # the ANSWERS page and after are skipped
        page = doc[pi]
        pno = pi + 1
        for rect, t in df.page_lines(page):
            if rect.y0 < cfg["top"] or rect.y0 >= cfg["bottom"]:
                continue
            if any(p == pno and r.contains(pymupdf.Point((rect.x0 + rect.x1) / 2,
                                                         (rect.y0 + rect.y1) / 2))
                   for p, r in fig_boxes):
                continue                      # inside a picture/table: the image carries it
            stripped = t.strip()
            # marks like "[3]" can be printed a few points above/below their "(i)":
            # attach them to the NEAREST marker on the page instead of the previous one
            if re.fullmatch(r"\[\s*\d+\s*\]", stripped):
                near = [(abs(ey - rect.y0), key) for ep, ey, key in events
                        if ep == pno and abs(ey - rect.y0) <= 12]
                cur = min(near, key=lambda n: n[0])[1] if near else None
            else:
                cur = None
            if cur is None:
                for ep, ey, key in events:
                    if (ep, ey) <= (pno, rect.y0 + 2):
                        cur = key
                    else:
                        break
            if cur is None:
                continue
            kind, q, roman = cur
            key = (q, roman)
            ymid = (rect.y0 + rect.y1) / 2
            is_margin = rect.x0 >= cfg["margin_x"] and bool(re.match(r"^\[", stripped))
            is_margin = is_margin or (rect.x0 >= cfg["margin_x"] and stripped.endswith("]")
                                      and cfg["margin_x"] < 480)
            if is_margin:
                margin_pieces.setdefault(key, []).append((pno, ymid, rect.x0, stripped))
                continue
            if JUNK_LINE_RE.match(stripped):
                continue
            # a "[1]" printed on the same line as the question text -> it is the marks
            inline = re.search(r"\s*(\[\s*\d+\s*\])\s*$", t)
            if inline:
                margin_pieces.setdefault(key, []).append((pno, ymid, rect.x1, inline.group(1)))
                t = t[:inline.start()]
            text_pieces.setdefault(key, []).append((pno, ymid, rect.x0, t))
        for ep, ey, key in events:
            if ep == pno and key[0] == "S":
                page_of.setdefault((key[1], key[2]), pno)

    # ---- assemble rows
    rows = []
    subs = [(k[1], k[2]) for _, _, k in events if k[0] == "S"]
    q_order = sorted({q for q, _ in subs})
    for q in q_order:
        parts = [r for (qq, r) in subs if qq == q]
        # lead-in text/margin printed under "Question N"
        pre_lines = join_visual_lines(text_pieces.get((q, ""), []))
        pre_lines = [l for l in pre_lines if not QUESTION_LINE_RE.match(l.strip()) or
                     tidy(QUESTION_LINE_RE.sub("", l))]
        pre_lines = [tidy(QUESTION_LINE_RE.sub("", l)) for l in pre_lines]
        pre_lines = [l for l in pre_lines if l]
        if q == 1:
            pre_lines = []                    # "Choose the correct answers ..." is only an instruction
        preamble = " ".join(pre_lines)
        q_total = None
        pm = " ".join(t for *_, t in sorted(margin_pieces.get((q, ""), [])))
        mm = MARKS_RE.search(pm)
        if mm:
            q_total = int(mm.group(1))

        q_rows = []
        for roman in parts:
            body = join_visual_lines(text_pieces.get((q, roman), []))
            body = [tidy(SUBMARK_RE.sub("", l, count=1)) if i == 0 else tidy(l)
                    for i, l in enumerate(body)]
            text = tidy(" ".join(b for b in body if b))
            if preamble:
                text = f"{preamble} {text}"
            mtxt = " ".join(t for *_, t in sorted(margin_pieces.get((q, roman), [])))
            mk = MARKS_RE.search(mtxt)
            marks = int(mk.group(1)) if mk else None
            rest = MARKS_RE.sub(" ", mtxt)
            tg = TAG_RE.search(tidy(rest))
            q_rows.append(dict(
                paper_no=cfg["paper_no"], question_number=q, sub_part=roman,
                marks=marks, question_text=text,
                competency_tag=tidy(tg.group(1)) if tg else "",
                pdf_page=page_of.get((q, roman), ""), source=name))
        # MCQ block printed as "[16]" with no per-part marks: share equally
        missing = [r for r in q_rows if r["marks"] is None]
        if missing and q_total:
            known = sum(r["marks"] for r in q_rows if r["marks"] is not None)
            share = (q_total - known) / len(missing)
            for r in missing:
                r["marks"] = int(share) if share == int(share) else share
        rows.extend(q_rows)

    # ---- pictures -> owners (preamble pictures go to every part of the question)
    by_row = {}
    for f in figures:
        if not f.owner:
            continue
        q, roman = f.owner
        targets = [r for r in rows if r["question_number"] == q and
                   (roman == "" or r["sub_part"] == roman)]
        for r in targets:
            by_row.setdefault((r["question_number"], r["sub_part"]), []).append(f)
    return rows, by_row


def main():
    DIAGRAMS_FOLDER.mkdir(exist_ok=True)
    RAW_CSV.parent.mkdir(exist_ok=True)
    for old in DIAGRAMS_FOLDER.glob("*.png"):
        old.unlink()

    docs, all_rows, figmap = {}, [], {}
    for name, cfg in PAPERS.items():
        if not (PDF_FOLDER / f"{name}.pdf").exists():
            print("missing:", name)
            continue
        rows, by_row = parse_paper(name, cfg, docs)
        for r in rows:
            r["_figs"] = by_row.get((r["question_number"], r["sub_part"]), [])
        all_rows.extend(rows)
        print(f"{name}: {len(rows)} rows, {sum(1 for r in rows if r['_figs'])} with a picture/table")

    # ---- ids + crops (a picture shared by several parts is saved once)
    saved = {}
    for n, r in enumerate(all_rows, start=1):
        r["question_id"] = f"Q{n:03d}"
        r["has_diagram"], r["diagram_image"] = "No", ""
        if not r["_figs"]:
            continue
        names = []
        for gi, g in enumerate(group_figures(r["_figs"]), start=1):
            ck = (r["source"], g["page"], tuple(round(v) for v in g["rect"]))
            if ck not in saved:
                page = docs[r["source"]][g["page"] - 1]
                clip = g["rect"] & page.rect
                fname = f'{r["question_id"]}.png' if len(group_figures(r["_figs"])) == 1 \
                    else f'{r["question_id"]}_{gi}.png'
                page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip).save(DIAGRAMS_FOLDER / fname)
                saved[ck] = f"diagrams/{fname}"
            names.append(saved[ck])
        r["has_diagram"], r["diagram_image"] = "Yes", ",".join(names)

    fields = ["question_id", "source", "paper_no", "question_number", "sub_part", "marks",
              "question_text", "has_diagram", "diagram_image", "pdf_page", "competency_tag"]
    with open(RAW_CSV, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r[k] for k in fields})
    print(f"Rows: {len(all_rows)} | picture files: {len(list(DIAGRAMS_FOLDER.glob('*.png')))} -> {RAW_CSV.name}")


if __name__ == "__main__":
    main()
