from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.core.database import SessionLocal
from app.models.submission import Student
from app.schemas.adaptive import AdaptivePaperRequest
from app.services.adaptive_engine import AdaptivePaperEngine

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

def test_closed_adaptive_loop():
    console.print(Panel("[bold green]Testing Adaptive Paper Generation (Closed Feedback Loop)[/bold green]"))

    db = SessionLocal()
    try:
        student = db.query(Student).first()
        if not student:
            console.print("[red]No student found! Run previous stages first.[/red]")
            return

        engine = AdaptivePaperEngine(db)

        console.print(f"[cyan]Analyzing Knowledge Profile for {student.name} and generating Adaptive Exam...[/cyan]\n")

        req = AdaptivePaperRequest(
            student_id=student.id,
            title="Personalized Remedial Math Exam",
            total_marks=5.0,
            duration_minutes=25,
            focus_mode="REMEDIAL"
        )

        result = engine.generate_adaptive_paper(req)

        # 1. Rationale Panel
        rationale_panel = f"""
[bold]Student:[/bold] {result.student_name} (ID: #{result.student_id})
[bold]Paper ID:[/bold] #{result.paper_details.paper_id} - {result.paper_details.title}
[bold]Total Marks Generated:[/bold] [bold green]{result.paper_details.total_marks}[/bold green]
[bold]Pedagogical Rationale:[/bold] [italic]{result.pedagogical_rationale}[/italic]
        """
        console.print(Panel(rationale_panel.strip(), title="Adaptive Engine Diagnosis", expand=False))

        # 2. Topic Allocation Table
        table = Table(title="Adaptive Weightage Allocation Summary")
        table.add_column("Topic Name", style="bold")
        table.add_column("Student Mastery Status", justify="center")
        table.add_column("Allocated Marks", justify="center")
        table.add_column("Questions Picked", justify="center")

        for item in result.topic_allocation_summary:
            color = "red" if "WEAK" in item.status else ("yellow" if "MODERATE" in item.status else "green")
            table.add_row(
                item.topic_name,
                f"[{color}]{item.status}[/{color}]",
                str(item.allocated_marks),
                str(item.questions_count)
            )

        console.print(table)

        # 3. Paper Questions Table
        q_table = Table(title="Personalized Exam Questions")
        q_table.add_column("Q#", justify="center")
        q_table.add_column("Type", justify="center")
        q_table.add_column("Marks", justify="center")
        q_table.add_column("Question Preview")

        for section_name, questions in result.paper_details.sections.items():
            for q in questions:
                q_table.add_row(
                    str(q.question_number),
                    q.question_type,
                    str(q.marks),
                    q.question_text[:55] + "..."
                )

        console.print(q_table)

        html_path = f"data/generated_papers/paper_{result.paper_details.paper_id}.html"
        console.print(f"\n[bold green]✓ Complete Closed Feedback Loop Successful![/bold green]")
        console.print(f"Printable Personalized Paper generated at: [yellow]{html_path}[/yellow]")

    except Exception as e:
        console.print(f"[bold red]Adaptive Loop Error:[/bold red] {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_closed_adaptive_loop()