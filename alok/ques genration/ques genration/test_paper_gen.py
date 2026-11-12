import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure Windows terminal encoding safety
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.core.database import engine, Base, SessionLocal
from app.models.taxonomy import Subject
from app.models.question import QuestionType
from app.schemas.paper import CustomPaperRequest, SectionRule
from app.services.paper_generator import PaperGeneratorEngine
from app.services.paper_renderer import PaperRenderer

console = Console()

def test_paper_generation():
    console.print(Panel("[bold green]Testing Question Paper Generation Engine (Constraint Solver)[/bold green]"))

    # Ensure paper tables are created in DB
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        subject = db.query(Subject).first()
        if not subject:
            console.print("[red]Subject not found. Run init_db.py first![/red]")
            return

        engine_service = PaperGeneratorEngine(db)

        # ----------------------------------------------------
        # TEST 1: Standard Paper
        # ----------------------------------------------------
        console.print("[cyan]Generating Standard Paper (Pattern: QUICK_TEST_10)...[/cyan]")
        std_paper = engine_service.generate_standard_paper(subject_id=subject.id, pattern_name="QUICK_TEST_10")
        std_file = PaperRenderer.render_to_html(std_paper)
        console.print(f"[green][PASS] Standard Paper Generated (ID: {std_paper.paper_id})[/green] -> [yellow]{std_file}[/yellow]")

        # ----------------------------------------------------
        # TEST 2: Custom Paper with Exact Constraint Verification
        # ----------------------------------------------------
        console.print("\n[cyan]Generating Custom Paper with Exact Marks Constraint...[/cyan]")
        custom_req = CustomPaperRequest(
            title="Class 10 CBSE Math - Quadratic Equations Diagnostic",
            subject_id=subject.id,
            total_marks=5.0,
            duration_minutes=25,
            sections=[
                SectionRule(
                    section_name="Section A: Concept MCQs",
                    question_type=QuestionType.MCQ,
                    marks_per_question=1.0,
                    question_count=1
                ),
                SectionRule(
                    section_name="Section B: Step Problems",
                    question_type=QuestionType.SHORT,
                    marks_per_question=2.0,
                    question_count=2
                )
            ]
        )
        custom_paper = engine_service.generate_custom_paper(custom_req)
        custom_file = PaperRenderer.render_to_html(custom_paper)
        console.print(f"[green][PASS] Custom Paper Generated (ID: {custom_paper.paper_id})[/green] -> [yellow]{custom_file}[/yellow]")

        # ----------------------------------------------------
        # Display Generated Paper Summary Table
        # ----------------------------------------------------
        table = Table(title=f"Generated Paper Preview: {custom_paper.title}")
        table.add_column("Q#", justify="center")
        table.add_column("Section")
        table.add_column("Type", justify="center")
        table.add_column("Marks", justify="center")
        table.add_column("Question Text")

        for section_name, questions in custom_paper.sections.items():
            for q in questions:
                table.add_row(
                    str(q.question_number),
                    section_name,
                    q.question_type,
                    str(q.marks),
                    q.question_text[:50] + "..."
                )

        console.print(table)
        console.print(f"\n[bold green]Printable HTML generated at:[/bold green] [underline]{custom_file}[/underline]")

    except Exception as e:
        console.print(f"[bold red]Generation Error:[/bold red] {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_paper_generation()