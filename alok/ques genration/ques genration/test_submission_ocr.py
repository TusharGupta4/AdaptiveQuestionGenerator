from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.core.database import engine, Base, SessionLocal
from app.models.paper import GeneratedPaper
from app.services.submission_service import SubmissionService

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

def test_submission():
    console.print(Panel("[bold cyan]Testing Answer Sheet OCR & Segmentation Pipeline[/bold cyan]"))

    # Ensure all tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Fetch the latest generated paper from Stage 4
        paper = db.query(GeneratedPaper).order_by(GeneratedPaper.id.desc()).first()
        if not paper:
            console.print("[red]No generated paper found! Run test_paper_gen.py first.[/red]")
            return

        console.print(f"[green]Testing against Generated Paper #{paper.id}: {paper.title}[/green]")

        service = SubmissionService(db)
        result = service.process_submission(
            paper_id=paper.id,
            student_roll="CBSE-10-9842",
            student_name="Aryan Sharma",
            file_path="data/sample_inputs/sample_student_answers.txt"
        )

        console.print(f"[bold green]✓ Submission #{result.submission_id} processed successfully![/bold green]")
        console.print(f"Student: [yellow]{result.student_name} ({result.roll_number})[/yellow]")
        console.print(f"Status: [magenta]{result.status}[/magenta]\n")

        # Display Segmented Mapping Table
        table = Table(title="Question-to-Answer Segmentation Table")
        table.add_column("Q#", justify="center")
        table.add_column("Question Text", style="cyan")
        table.add_column("Allocated Marks", justify="center")
        table.add_column("Segmented Student Answer", style="green")

        for ans in result.answers:
            table.add_row(
                str(ans.question_number),
                ans.question_text[:40] + "...",
                str(ans.marks_allocated),
                ans.student_answer_text[:50] + "..."
            )

        console.print(table)
        console.print("\n[bold green]Ready for Stage 6: Rubric-Based Evaluation Engine![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Error in submission pipeline:[/bold red] {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_submission()