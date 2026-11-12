from pathlib import Path
from app.schemas.paper import GeneratedPaperResponse

OUTPUT_DIR = Path("data/generated_papers")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

class PaperRenderer:
    @staticmethod
    def render_to_html(paper: GeneratedPaperResponse) -> str:
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{paper.title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 40px auto;
            padding: 20px;
            color: #1a1a1a;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #333;
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .header h1 {{ margin: 0; font-size: 24px; text-transform: uppercase; }}
        .header h3 {{ margin: 5px 0; font-size: 16px; color: #555; }}
        .meta {{
            display: flex;
            justify-content: space-between;
            margin-top: 15px;
            font-weight: bold;
            font-size: 14px;
        }}
        .section-header {{
            background: #f1f3f5;
            padding: 8px 15px;
            margin: 25px 0 15px 0;
            border-left: 4px solid #228be6;
            font-weight: bold;
            font-size: 16px;
        }}
        .question-block {{
            margin-bottom: 20px;
            padding-left: 10px;
        }}
        .q-header {{
            display: flex;
            justify-content: space-between;
            font-weight: 600;
        }}
        .marks-tag {{
            color: #d6336c;
            font-size: 13px;
        }}
        .options-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            margin-top: 10px;
            padding-left: 20px;
        }}
        .option {{
            font-size: 14px;
        }}
        @media print {{
            body {{ margin: 0; padding: 10px; }}
            .section-header {{ background: #e9ecef !important; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{paper.title}</h1>
        <h3>Subject: {paper.subject_name}</h3>
        <div class="meta">
            <span>Time: {paper.duration_minutes} Mins</span>
            <span>Paper ID: #{paper.paper_id}</span>
            <span>Total Marks: {paper.total_marks}</span>
        </div>
    </div>
"""
        for section_name, questions in paper.sections.items():
            html += f'<div class="section-header">{section_name}</div>\n'
            for q in questions:
                html += f"""
    <div class="question-block">
        <div class="q-header">
            <span><strong>Q{q.question_number}.</strong> {q.question_text}</span>
            <span class="marks-tag">[{int(q.marks) if q.marks.is_integer() else q.marks} Mark{'s' if q.marks > 1 else ''}]</span>
        </div>
"""
                if q.options:
                    html += '<div class="options-grid">\n'
                    for opt in q.options:
                        html += f'<div class="option">({opt["label"]}) {opt["text"]}</div>\n'
                    html += '</div>\n'

                html += '</div>\n'

        html += """
</body>
</html>
"""
        file_path = OUTPUT_DIR / f"paper_{paper.paper_id}.html"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)

        return str(file_path)