from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.core.database import SessionLocal
from app.models.submission import StudentSubmission
from app.services.evaluation_service import EvaluationService

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

def test_evaluation():
    console.print(Panel("[bold green]Testing Multi-Criteria Rubric Evaluation Engine[/bold green]"))

    db = SessionLocal()
    try:
        # Fetch the latest submission from Stage 5
        submission = db.query(StudentSubmission).order_by(StudentSubmission.id.desc()).first()
        if not submission:
            console.print("[red]No submission found! Run test_submission_ocr.py first.[/red]")
            return

        console.print(f"[cyan]Evaluating Submission #{submission.id} for Student: {submission.student.name}...[/cyan]\n")

        service = EvaluationService(db)
        report = service.evaluate_submission(submission.id)

        # 1. Overall Scorecard Panel
        score_panel = f"""
[bold]Student:[/bold] {report.student_name} ({report.roll_number})
[bold]Exam Paper:[/bold] {report.paper_title}
[bold]Total Marks:[/bold] {report.total_paper_marks}
[bold]Marks Obtained:[/bold] [green]{report.total_score_obtained}[/green] / {report.total_paper_marks}
[bold]Percentage:[/bold] [bold magenta]{report.percentage}%[/bold magenta]
[bold]Status:[/bold] [yellow]{report.status}[/yellow]
        """
        console.print(Panel(score_panel.strip(), title="Student Official Scorecard", expand=False))

        # 2. Detailed Per-Question Step Breakdown Table
        table = Table(title="Per-Question Rubric Evaluation Breakdown")
        table.add_column("Q#", justify="center")
        table.add_column("Type", justify="center")
        table.add_column("Score", justify="center")
        table.add_column("Step Breakdown & Reasoning")

        for ans in report.detailed_answers:
            steps_text = []
            for s in ans.step_evaluations:
                icon = "✓" if s.is_satisfied else "✗"
                steps_text.append(f"{icon} [bold]{s.step_description}[/bold]: {s.marks_awarded}/{s.max_marks}m ({s.reasoning})")
            
            table.add_row(
                str(ans.question_number),
                ans.question_type,
                f"{ans.marks_awarded} / {ans.max_marks}",
                "\n".join(steps_text) if steps_text else ans.feedback
            )

        console.print(table)
        console.print("\n[bold green]✓ Evaluation Engine successfully completed and verified![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Evaluation Error:[/bold red] {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_evaluation()