import sys
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Ensure Windows terminal encoding safety
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console()
BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_endpoints():
    console.print(Panel("[bold cyan]Testing Question Bank REST API Endpoints[/bold cyan]"))

    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Test Syllabus Hierarchy
        resp = client.get("/syllabus/subjects")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        subjects = resp.json()
        console.print(f"[green][PASS] GET /syllabus/subjects[/green] -> Found {len(subjects)} subjects")
        
        # 2. Test Get All Questions
        resp = client.get("/questions")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        all_questions = resp.json()
        console.print(f"[green][PASS] GET /questions[/green] -> Found {len(all_questions)} total questions")

        # 3. Test Filtering (e.g. MCQ only)
        resp = client.get("/questions?question_type=MCQ")
        assert resp.status_code == 200
        mcqs = resp.json()
        console.print(f"[green][PASS] GET /questions?question_type=MCQ[/green] -> Found {len(mcqs)} MCQs")

        # 4. Test Search filter
        resp = client.get("/questions?search=roots")
        assert resp.status_code == 200
        search_results = resp.json()
        console.print(f"[green][PASS] GET /questions?search=roots[/green] -> Found {len(search_results)} questions matching 'roots'")

        # 5. Test Paper Generation
        if subjects:
            resp = client.post("/papers/generate/standard", json={"subject_id": subjects[0]["id"], "pattern_name": "QUICK_TEST_10"})
            assert resp.status_code == 200, f"Failed: {resp.text}"
            paper_data = resp.json()
            console.print(f"[green][PASS] POST /papers/generate/standard[/green] -> Generated Paper #{paper_data['paper_id']} ({paper_data['total_marks']} marks, {paper_data['total_questions']} questions)")

        # Display result sample
        table = Table(title="Live API Response Sample")
        table.add_column("ID", justify="center")
        table.add_column("Type", justify="center")
        table.add_column("Marks", justify="center")
        table.add_column("Difficulty", justify="center")
        table.add_column("Question Preview")

        for q in all_questions[:4]:
            table.add_row(str(q["id"]), q["question_type"], str(q["marks"]), q["difficulty"], q["question_text"][:45] + "...")

        console.print(table)
        console.print("[bold green]All API tests passed successfully![/bold green]")

if __name__ == "__main__":
    try:
        test_endpoints()
    except httpx.ConnectError:
        console.print("[bold red]Error:[/bold red] FastAPI server chal nahi raha hai.")
        console.print("Pehle terminal me run karein: [yellow]uvicorn app.main:app --reload[/yellow]")