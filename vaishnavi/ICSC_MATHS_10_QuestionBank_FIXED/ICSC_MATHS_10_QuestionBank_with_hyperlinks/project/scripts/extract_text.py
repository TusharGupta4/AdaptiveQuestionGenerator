"""
STEP 1 : PDF -> raw text
--------------------------------
Reads every PDF in /pdfs and dumps its text (page by page, with clear
"--- Page N ---" markers) into /extracted_text/<n>.txt

NEW: text that sits INSIDE a diagram / graph / table box is dropped here.
The figure is delivered as a cropped image (step 4), so its letters and
numbers (A, B, 60, 25 cm, axis ticks ...) must not leak into question_text
as junk like "P B D C A E 100 m 14 35".
"""

import sys
from pathlib import Path

import pymupdf  # (aka fitz)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagram_finder as df  # noqa: E402

project_folder = Path(__file__).parent.parent
pdf_folder = project_folder / "pdfs"
output_folder = project_folder / "extracted_text"
output_folder.mkdir(exist_ok=True)

pdf_files = sorted(pdf_folder.glob("*.pdf"))
if not pdf_files:
    print("No PDFs found in", pdf_folder)

for pdf_path in pdf_files:
    document = pymupdf.open(pdf_path)

    layout = df.PAPER_LAYOUT.get(pdf_path.stem)
    removed = 0
    if layout:
        figures, _ = df.locate(document, *layout)      # also strips the watermark
        for fig in figures:
            if fig.owner:
                document[fig.page - 1].add_redact_annot(fig.rect)
                removed += 1
        for page in document:
            if page.first_annot:                         # in-memory only, PDF file untouched
                page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                      graphics=pymupdf.PDF_REDACT_LINE_ART_NONE)

    extracted_text = ""
    for page_number, page in enumerate(document, start=1):
        extracted_text += f"\n\n--- Page {page_number} ---\n\n"
        extracted_text += page.get_text()

    output_path = output_folder / (pdf_path.stem + ".txt")
    output_path.write_text(extracted_text, encoding="utf-8")
    print(f"Text extracted: {pdf_path.name} -> {output_path.name} "
          f"({len(document)} pages, {removed} figure box(es) removed from text)")

print("Extraction completed.")
