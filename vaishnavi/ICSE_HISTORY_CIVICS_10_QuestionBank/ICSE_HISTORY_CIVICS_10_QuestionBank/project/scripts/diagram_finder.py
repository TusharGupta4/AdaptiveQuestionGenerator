r"""
diagram_finder.py  --  find the REAL bounding box of every diagram / graph /
table / bill in a question-paper PDF and say which sub-question owns it.

Why this exists
---------------
The old step 4 simply rendered the WHOLE PDF page next to every question that
mentioned the word "diagram".  A page holds 2-3 diagrams (and in the 2025 paper
two columns), so a student saw a full page of other questions + other figures.
Here we instead read the PDF's own geometry:

  1. Remove the watermark (2025: one big image, 2026: a tagged /Watermark
     artifact in the page content stream) so crops are clean.
  2. Collect "figure pieces" on each page: vector drawings (lines, circles,
     table borders, graph grids) and embedded pictures.
  3. Merge pieces that touch / sit close together into one figure, then pull
     in the short text labels around it (A, B, 60 deg, 25 cm, axis numbers ...).
  4. Walk the page in READING ORDER (left column -> right column -> next page)
     and give each figure to the sub-question marker ("(i)", "(ii)" ...) that
     came most recently before it.  Because ownership comes from position on
     the page and not from the text stream, it stays correct even when the PDF
     prints sub-questions out of order (the 2026 paper prints (i),(iii) on one
     page and (ii),(iv),(v) on the next).
"""

import re
from dataclasses import dataclass, field

import pymupdf

# Per paper: (two-column layout?, header band height in pt)
PAPER_LAYOUT = {
    "ICSE-10 History Civics (2025)": (False, 72),
    "ICSE-10 History Civics (2026)": (False, 0),
}

# History papers: pictures carry their own labels and option lines such as "(a)  China" sit
# right under them, so labels must NOT be pulled into the crop.
USE_LABELS = False

# ----------------------------------------------------------------- settings
MERGE_GAP = 10          # pt: drawing pieces closer than this become one figure
LABEL_GAP = 20          # pt: short text this close to a figure is a label of it
MIN_W, MIN_H = 30, 22   # pt: smaller "figures" are fraction bars / noise
PAD = 6                 # pt: white margin added around the final crop
FOOTER_Y = 712          # pt: nothing real is drawn below this (page footer)

ANSWER_HEADING_RE = re.compile(r"marking scheme|^ANSWERS?$", re.IGNORECASE)
QUESTION_RE = re.compile(r"^Question\s+(\d{1,2})\b", re.IGNORECASE)
SUBPART_RE = re.compile(r"^\(([ivxlc]{1,6})\)(?:\s|$)", re.IGNORECASE)
NOT_A_LABEL_RE = re.compile(
    r"^\([a-e]\)|^\([ivxl]+\)|^\[|^Question\b|^SECTION|^\d+\s*$", re.IGNORECASE)
ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def roman_to_int(s):
    s = s.lower()
    if not s or any(c not in ROMAN for c in s):
        return None
    total = prev = 0
    for ch in reversed(s):
        v = ROMAN[ch]
        total += -v if v < prev else v
        prev = max(prev, v)
    return total


# ------------------------------------------------------------ watermark kill
def strip_watermark(doc, page, repeated=()):
    """Remove the paper's watermark so crops come out clean."""
    # 2026 style: vector watermark wrapped in  /Artifact <</Subtype /Watermark>> BDC ... EMC
    for xref in page.get_contents():
        stream = doc.xref_stream(xref)
        if b"/Watermark" not in stream:
            continue
        txt = stream.decode("latin1")
        m = re.search(r"/Artifact\s*<<[^>]*?/Subtype\s*/Watermark[^>]*?>>\s*BDC", txt)
        if not m:
            continue
        depth, pos, end = 1, m.end(), None
        for t in re.finditer(r"\bBDC\b|\bBMC\b|\bEMC\b", txt[pos:]):
            depth += -1 if t.group() == "EMC" else 1
            if depth == 0:
                end = pos + t.end()
                break
        if end:
            doc.update_stream(xref, (txt[:m.start()] + txt[end:]).encode("latin1"))
    # 2025 style: one huge picture behind the text
    area = page.rect.width * page.rect.height
    for im in page.get_image_info(xrefs=True):
        r = pymupdf.Rect(im["bbox"])
        if im.get("xref") and (r.width * r.height > 0.4 * area or im["xref"] in repeated):
            page.delete_image(im["xref"])


# ------------------------------------------------------------------- helpers
def _merge(rects, gap):
    """Union rectangles that are within `gap` of each other (repeat until stable)."""
    rects = [pymupdf.Rect(r) for r in rects]
    changed = True
    while changed:
        changed = False
        out = []
        for r in rects:
            for i, o in enumerate(out):
                if (r + (-gap / 2, -gap / 2, gap / 2, gap / 2)).intersects(
                        o + (-gap / 2, -gap / 2, gap / 2, gap / 2)):
                    out[i] = o | r
                    changed = True
                    break
            else:
                out.append(r)
        rects = out
    return rects


@dataclass
class Figure:
    page: int                      # 1-based page number
    col: int
    rect: pymupdf.Rect
    owner: tuple = None            # (question_number, roman)


@dataclass
class Marker:
    page: int
    col: int
    y: float
    kind: str                      # "Q" or "sub"
    value: object                  # int question number or roman string
    owner: tuple = None            # (question_number, roman) once accepted as a real sub-question


def page_lines(page, with_block=False):
    out = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        longest = max((len("".join(s["text"] for s in l["spans"]).strip()) for l in b["lines"]),
                      default=0)
        for l in b["lines"]:
            t = "".join(s["text"] for s in l["spans"]).strip()
            t = "".join(ch for ch in t if ch == "\t" or ord(ch) >= 32).strip()
            if t:
                out.append((pymupdf.Rect(l["bbox"]), t, longest) if with_block
                           else (pymupdf.Rect(l["bbox"]), t))
    return out


def find_last_page(doc):
    """Index of the page holding the ANSWERS / MARKING SCHEME heading."""
    for pi, page in enumerate(doc):
        for _, t in page_lines(page):
            if ANSWER_HEADING_RE.search(t):
                return pi
    return len(doc) - 1


def figures_on_page(page, lines, header_y, two_col=False):   # lines = page_lines(page, with_block=True)
    """Figure rectangles on one page (before ownership is decided)."""
    area = page.rect.width * page.rect.height
    pieces = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.y1 < header_y or r.y0 > FOOTER_Y:
            continue                                   # header ornament / footer rule
        if r.width * r.height > 0.5 * area:
            continue                                   # page-sized background
        pieces.append(pymupdf.Rect(r.x0, r.y0, max(r.x1, r.x0 + .01), max(r.y1, r.y0 + .01)))
    for im in page.get_image_info():
        r = pymupdf.Rect(im["bbox"])
        if r.width * r.height > 0.4 * area or r.y0 > FOOTER_Y:
            continue
        pieces.append(r)

    figs = _merge(pieces, MERGE_GAP)
    figs = [f for f in figs if f.width >= MIN_W and f.height >= MIN_H]
    bases = [pymupdf.Rect(f) for f in figs]         # the drawings alone, before labels

    # pull in short labels (A, B, 60 deg, 25 cm, axis numbers ...) around each figure
    # a label lives in a block made only of short lines (A, B, 60 deg, 25 cm ...);
    # the tail of a paragraph ("cm.", "distribution:") does not.
    labels = [(r, t) for r, t, longest in lines
              if USE_LABELS and longest <= 14 and not t.endswith((":", ".", ",", ";"))
              and not NOT_A_LABEL_RE.match(t)]
    for _ in range(3):
        grew = False
        for i, f in enumerate(figs):
            probe = f + (-LABEL_GAP, -LABEL_GAP, LABEL_GAP, LABEL_GAP)
            fcol = (f.x0 + f.x1) / 2 >= page.rect.width / 2
            for r, _t in labels:
                if two_col and ((r.x0 + r.x1) / 2 >= page.rect.width / 2) != fcol:
                    continue                       # a label never crosses the column gutter
                if probe.intersects(r) and not f.contains(r):
                    figs[i] = f = f | r
                    probe = f + (-LABEL_GAP, -LABEL_GAP, LABEL_GAP, LABEL_GAP)
                    grew = True
        figs = _merge(figs, 2)
        if not grew:
            break

    # trim: never cut the drawing itself, but shave off any ordinary paragraph line
    # that the labels dragged the crop into (half-visible text looks broken)
    label_set = {(tuple(r), t) for r, t in labels}
    paragraph = [r for r, t, _n in lines if (tuple(r), t) not in label_set]
    out = []
    for f in figs:
        core = None
        for b in bases:
            if f.contains(b):
                core = b if core is None else core | b
        core = core or f
        for r in paragraph:
            if f.intersects(r):
                # text line sitting on / just above the top edge, or just below the bottom edge
                if r.y0 < core.y0 and r.y1 <= core.y0 + 5:
                    f.y0 = max(f.y0, r.y1 + .3)
                elif r.y1 > core.y1 and r.y0 >= core.y1 - 5:
                    f.y1 = min(f.y1, r.y0 - .3)
        # white margin around the crop, but never into a neighbouring paragraph line
        p = pymupdf.Rect(f.x0 - PAD, f.y0 - PAD, f.x1 + PAD, f.y1 + PAD)
        for r in paragraph:
            if p.intersects(r) and not f.intersects(r):
                if r.y1 <= f.y0 + .5:
                    p.y0 = max(p.y0, r.y1 + .3)
                elif r.y0 >= f.y1 - .5:
                    p.y1 = min(p.y1, r.y0 - .3)
        if header_y:
            p.y0 = max(p.y0, header_y - 5)      # keep the page-header ornament out of the crop
        out.append(p & page.rect)
    return out


def locate(doc, two_col, header_y=0):
    """
    Returns (figures, markers) for one PDF, in reading order, restricted to the
    real question pages (everything from the ANSWERS heading on is ignored).
    """
    last = find_last_page(doc)
    # a picture that shows up on many pages is the paper's watermark, not a figure
    counts = {}
    for page in doc:
        for im in page.get_image_info(xrefs=True):
            if im.get("xref"):
                counts[im["xref"]] = counts.get(im["xref"], 0) + 1
    repeated = {x for x, n in counts.items() if n >= 4}
    figures, markers = [], []
    # the page that holds the ANSWERS heading: skip it if the heading is near its top
    for pi in range(last + 1):
        page = doc[pi]
        if pi == last:
            hy = min((r.y0 for r, t in page_lines(page) if ANSWER_HEADING_RE.search(t)), default=0)
            if hy < 200:
                break
        strip_watermark(doc, page, repeated)
        blines = page_lines(page, with_block=True)
        lines = [(r, t) for r, t, _n in blines]
        mid = page.rect.width / 2

        def col_of(x0):
            return 1 if (two_col and x0 >= mid - 4) else 0

        # --- markers: "Question N" and "(i)", "(ii)" ... at the left edge of a column
        for r, t in lines:
            c = col_of(r.x0)
            col_left = 294 if c else 54          # left edge where "(i)" / "Question" start
            if QUESTION_RE.match(t):
                markers.append(Marker(pi + 1, c, r.y0, "Q", int(QUESTION_RE.match(t).group(1))))
                continue
            m = SUBPART_RE.match(t)
            if m and (col_left - 14) <= r.x0 <= col_left + 14:
                val = roman_to_int(m.group(1))
                if val and 1 <= val <= 20:
                    markers.append(Marker(pi + 1, c, r.y0, "sub", m.group(1).lower()))

        for f in figures_on_page(page, blines, header_y, two_col):
            figures.append(Figure(pi + 1, col_of(f.x0), f))

    # --- reading order + ownership
    events = [(m.page, m.col, m.y, 0, m) for m in markers] + \
             [(f.page, f.col, f.rect.y0, 1, f) for f in figures]
    events.sort(key=lambda e: e[:4])
    q = None
    seen = {}
    cur = None
    for _p, _c, _y, _k, obj in events:
        if isinstance(obj, Marker):
            if obj.kind == "Q":
                q = obj.value
                seen[q] = set()
                cur = (q, "")          # preamble: figures here belong to every part of Q
            else:
                # (c)/(d) are valid roman numerals too, but are capped at 20 above;
                # a roman already used in this question is an option, not a new part.
                if q is not None and obj.value not in seen.get(q, set()):
                    seen[q].add(obj.value)
                    cur = (q, obj.value)
                    obj.owner = cur
        else:
            obj.owner = cur
    return figures, markers
