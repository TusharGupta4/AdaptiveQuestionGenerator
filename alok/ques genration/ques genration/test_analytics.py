from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from app.core.database import engine, Base, SessionLocal
from app.models.submission import Student
from app.services.analytics_service import AnalyticsService

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()

def test_analytics():
    console.print(Panel("[bold green]Testing Student Knowledge Profile & Analytics Engine[/bold green]"))

    # Ensure profile tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        student = db.query(Student).first()
        if not student:
            console.print("[red]No student found. Run previous stages first![/red]")
            return

        service = AnalyticsService(db)
        profile = service.generate_student_profile(student.id)

        # 1. Summary Panel
        summary = f"""
[bold]Student:[/bold] {profile.student_name} ({profile.roll_number})
[bold]Overall Accuracy:[/bold] [bold cyan]{profile.overall_accuracy}%[/bold cyan]
[bold]Questions Evaluated:[/bold] {profile.total_questions_attempted}

[bold green]Strong Topics (≥75%):[/bold green] {', '.join(profile.strong_topics) if profile.strong_topics else 'None yet'}
[bold yellow]Moderate Topics (40-74%):[/bold yellow] {', '.join(profile.moderate_topics) if profile.moderate_topics else 'None'}
[bold red]Weak Topics (<40%):[/bold red] {', '.join(profile.weak_topics) if profile.weak_topics else 'None'}
        """
        console.print(Panel(summary.strip(), title="Student Knowledge Matrix", expand=False))

        # 2. Detailed Topic Performance Table
        table = Table(title="Chapter & Topic Mastery Breakdown")
        table.add_column("Chapter", style="cyan")
        table.add_column("Topic", style="bold")
        table.add_column("Score", justify="center")
        table.add_column("Accuracy", justify="center")
        table.add_column("Status", justify="center")

        for t in profile.topic_performance:
            color = "green" if t.status.value == "STRONG" else ("yellow" if t.status.value == "MODERATE" else "red")
            table.add_row(
                t.chapter_name,
                t.topic_name,
                f"{t.marks_obtained} / {t.marks_possible}",
                f"{t.accuracy_percentage}%",
                f"[{color}]{t.status.value}[/{color}]"
            )

        console.print(table)

        # 3. Actionable Recommendations
        console.print("\n[bold cyan]Pedagogical Recommendations for Next Paper:[/bold cyan]")
        for r in profile.recommendations:
            console.print(f"  💡 {r}")

        console.print("\n[bold green]✓ Knowledge Profile successfully generated and ready for Stage 8 Adaptive Loop![/bold green]")

    except Exception as e:
        console.print(f"[bold red]Analytics Error:[/bold red] {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    test_analytics()