import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.table import Table
from app.core.database import SessionLocal
from app.services.ingestion_service import IngestionService
from app.models.question import Question

console = Console()

def run_ingestion():
    file_path = "data/sample_inputs/sample_paper.txt"
    console.print(f"[bold cyan]Starting ingestion for:[/bold cyan] {file_path}")

    db = SessionLocal()
    try:
        service = IngestionService(db)
        count = service.ingest_file(file_path)
        console.print(f"[bold green]Successfully ingested {count} questions into the database![/bold green]\n")

        # Display all questions in DB
        table = Table(title="Updated Question Bank in DB")
        table.add_column("ID", justify="center")
        table.add_column("Type", justify="center")
        table.add_column("Marks", justify="center")
        table.add_column("Difficulty", justify="center")
        table.add_column("Topic ID", justify="center")
        table.add_column("Question Text")

        for q in db.query(Question).all():
            table.add_row(
                str(q.id),
                q.question_type.value,
                str(q.marks),
                q.difficulty.value,
                str(q.topic_id),
                q.question_text[:50] + "..."
            )

        console.print(table)

    except Exception as e:
        console.print(f"[bold red]Ingestion Error:[/bold red] {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    run_ingestion()