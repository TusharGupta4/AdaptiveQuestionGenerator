import io
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib import colors
from portal.core.database import GeneratedPaper, PaperQuestion

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class PDFExportService:
    @staticmethod
    def generate_exam_pdf(paper: GeneratedPaper) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40, leftMargin=40,
            topMargin=40, bottomMargin=40
        )
        
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'ExamTitle',
            parent=styles['Heading1'],
            fontSize=16,
            leading=20,
            alignment=1, # Center
            textColor=colors.HexColor("#1A365D")
        )
        subtitle_style = ParagraphStyle(
            'ExamSubTitle',
            parent=styles['Normal'],
            fontSize=11,
            leading=14,
            alignment=1,
            textColor=colors.HexColor("#4A5568")
        )
        section_style = ParagraphStyle(
            'ExamSection',
            parent=styles['Heading2'],
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#2B6CB0"),
            spaceBefore=10,
            spaceAfter=5
        )
        q_style = ParagraphStyle(
            'ExamQuestion',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#1A202C")
        )
        opt_style = ParagraphStyle(
            'ExamOption',
            parent=styles['Normal'],
            fontSize=9,
            leading=12,
            leftIndent=15,
            textColor=colors.HexColor("#2D3748")
        )

        elements = []

        # 1. Header
        board_name = paper.board.name if paper.board else "Standard Examination"
        elements.append(Paragraph(f"<b>{paper.title.upper()}</b>", title_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(f"{board_name} | Total Marks: {paper.total_marks} | Duration: {paper.duration_minutes} Mins", subtitle_style))
        elements.append(Spacer(1, 10))

        # Horizontal Divider
        divider = Table([[""]], colWidths=[530], rowHeights=[1])
        divider.setStyle(TableStyle([('LINEABOVE', (0, 0), (-1, -1), 1.5, colors.HexColor("#CBD5E0"))]))
        elements.append(divider)
        elements.append(Spacer(1, 10))

        # Instructions
        inst_text = "<b>General Instructions:</b><br/>" \
                    "1. All questions are compulsory unless internal choice is specified.<br/>" \
                    "2. Marks allocated to each question are indicated against it.<br/>" \
                    "3. Read all questions carefully before attempting."
        elements.append(Paragraph(inst_text, subtitle_style))
        elements.append(Spacer(1, 15))

        # 2. Questions Grouped by Section
        current_section = None
        for pq in paper.paper_questions:
            q = pq.question
            sec_name = pq.section_name or "Questions"
            
            if sec_name != current_section:
                current_section = sec_name
                elements.append(Paragraph(f"<b>{current_section}</b>", section_style))
                elements.append(Spacer(1, 5))

            sub_part_str = f"({q.sub_part}) " if q.sub_part else ""
            q_header = f"<b>Q{pq.question_number}. {sub_part_str}</b>{q.question_text} <font color='#718096'><b>[{pq.allocated_marks} Mark(s)]</b></font>"
            elements.append(Paragraph(q_header, q_style))
            elements.append(Spacer(1, 4))

            # Render Diagram Image if available
            if q.has_diagram and q.diagram_url:
                local_img_path = BASE_DIR / q.diagram_url
                if local_img_path.exists():
                    try:
                        img = RLImage(str(local_img_path), width=250, height=140)
                        elements.append(img)
                        elements.append(Spacer(1, 5))
                    except Exception:
                        pass

            # Render MCQ options if applicable
            if q.options and isinstance(q.options, dict):
                for opt_key, opt_val in q.options.items():
                    elements.append(Paragraph(f"<b>({opt_key})</b> {opt_val}", opt_style))
                elements.append(Spacer(1, 4))

            elements.append(Spacer(1, 6))

        doc.build(elements)
        buffer.seek(0)
        return buffer.getvalue()
