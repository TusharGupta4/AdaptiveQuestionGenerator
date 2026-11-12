import os
import sys
from pathlib import Path

# Fix Windows console encoding if needed
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.panel import Panel
from app.core.config import settings

console = Console()

def check_gemini():
    console.print(Panel.fit("[bold cyan]Gemini AI Connectivity & Status Check[/bold cyan]"))
    
    # 1. Check API Key
    api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
    if not api_key:
        console.print("[bold red][ERROR] GEMINI_API_KEY is not configured in file.env or environment variables![/bold red]")
        return False
    
    masked_key = api_key[:6] + "..." + api_key[-4:]
    console.print(f"[bold green][OK][/bold green] API Key detected: [yellow]{masked_key}[/yellow]")
    
    # 2. Test Direct Connection to Gemini
    console.print("[cyan]Connecting to Gemini (gemini-3.8-flash)...[/cyan]")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
            contents="Respond with 'Gemini AI is active and online!' and nothing else."
        )
        console.print(f"[bold green][OK] Direct Gemini Call Successful:[/bold green] {response.text.strip()}")
    except Exception as e:
        console.print(f"[bold red][ERROR] Direct Gemini Call Failed:[/bold red] {e}")
        return False

    # 3. Test QuestionStructurer Integration
    console.print("\n[cyan]Testing QuestionStructurer parsing with Gemini...[/cyan]")
    try:
        from app.services.question_structurer import QuestionStructurer
        sample_text = (
            "Class 10 Mathematics\n"
            "Q1. Find the roots of x^2 - 5x + 6 = 0.\n"
            "[Marks: 2]\n"
            "[Chapter: Quadratic Equations]\n"
            "[Topic: Factorisation]\n"
            "[Answer: x = 2, 3]"
        )
        paper = QuestionStructurer.parse_paper(sample_text)
        console.print("[bold green][OK] Question Structurer Parsed Successfully![/bold green]")
        console.print(f"  - Subject: [bold]{paper.subject}[/bold]")
        console.print(f"  - Grade: [bold]{paper.grade}[/bold]")
        console.print(f"  - Questions Extracted: [bold]{len(paper.questions)}[/bold]")
        if paper.questions:
            q = paper.questions[0]
            console.print(f"  - Question 1: [italic]{q.question_text}[/italic]")
            console.print(f"  - Type: {q.question_type}, Marks: {q.marks}, Difficulty: {q.difficulty}")
            if q.rubric_steps:
                console.print(f"  - Generated Rubric Steps: {len(q.rubric_steps)} steps")
    except Exception as e:
        console.print(f"[bold red][ERROR] QuestionStructurer Parsing Failed:[/bold red] {e}")
        return False

    console.print("\n[bold green][SUCCESS] All AI checks passed successfully! Gemini is active and working.[/bold green]")
    return True

if __name__ == "__main__":
    check_gemini()
