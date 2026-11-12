import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from rich.console import Console
from rich.table import Table
from app.core.database import engine, Base, SessionLocal
from app.models import (
    Subject, Chapter, Topic, Subtopic, 
    Question, QuestionOption, QuestionType, DifficultyLevel
)

console = Console()

def init_database():
    console.print("[bold green]Creating database tables...[/bold green]")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if already seeded
        if db.query(Subject).first():
            console.print("[yellow]Database already contains data. Skipping seeding.[/yellow]")
            return

        console.print("[cyan]Seeding sample syllabus (Class 10 Mathematics)...[/cyan]")
        
        # 1. Subject
        math = Subject(name="Mathematics", grade="Class 10", board="CBSE")
        db.add(math)
        db.flush()

        # 2. Chapters
        ch1 = Chapter(name="Quadratic Equations", chapter_number=4, subject_id=math.id)
        ch2 = Chapter(name="Arithmetic Progressions", chapter_number=5, subject_id=math.id)
        db.add_all([ch1, ch2])
        db.flush()

        # 3. Topics
        top1 = Topic(name="Nature of Roots", chapter_id=ch1.id)
        top2 = Topic(name="Solution by Factorisation", chapter_id=ch1.id)
        top3 = Topic(name="nth Term of an AP", chapter_id=ch2.id)
        db.add_all([top1, top2, top3])
        db.flush()

        # 4. Subtopics
        sub1 = Subtopic(name="Discriminant Conditions (D > 0, D = 0, D < 0)", topic_id=top1.id)
        sub2 = Subtopic(name="Word Problems", topic_id=top2.id)
        db.add_all([sub1, sub2])
        db.flush()

        # 5. Sample Questions
        # Q1: MCQ on Discriminant
        q1 = Question(
            question_text="For what value of k does the quadratic equation 2x^2 + kx + 3 = 0 have two equal real roots?",
            question_type=QuestionType.MCQ,
            marks=1.0,
            difficulty=DifficultyLevel.EASY,
            expected_answer="Option B: ±2√6",
            rubric_steps=[{"step": "Formula D = b^2 - 4ac = 0", "marks": 0.5}, {"step": "Solve for k", "marks": 0.5}],
            source="CBSE Board 2022",
            topic_id=top1.id,
            subtopic_id=sub1.id
        )
        db.add(q1)
        db.flush()

        options = [
            QuestionOption(question_id=q1.id, option_label="A", option_text="±4", is_correct=0),
            QuestionOption(question_id=q1.id, option_label="B", option_text="±2√6", is_correct=1),
            QuestionOption(question_id=q1.id, option_label="C", option_text="±6", is_correct=0),
            QuestionOption(question_id=q1.id, option_label="D", option_text="0", is_correct=0),
        ]
        db.add_all(options)

        # Q2: Short Answer
        q2 = Question(
            question_text="Find the roots of the quadratic equation 6x^2 - x - 2 = 0 by factorisation.",
            question_type=QuestionType.SHORT,
            marks=2.0,
            difficulty=DifficultyLevel.MEDIUM,
            expected_answer="x = 2/3 and x = -1/2",
            rubric_steps=[
                {"step": "Split middle term: 6x^2 - 4x + 3x - 2 = 0", "marks": 1.0},
                {"step": "Factorise to (2x + 1)(3x - 2) = 0 and solve", "marks": 1.0}
            ],
            source="NCERT",
            topic_id=top2.id,
            subtopic_id=None
        )
        db.add(q2)

        # Q3: Numerical / Long
        q3 = Question(
            question_text="Find the 20th term from the last term of the AP: 3, 8, 13, ..., 253.",
            question_type=QuestionType.NUMERICAL,
            marks=3.0,
            difficulty=DifficultyLevel.HARD,
            expected_answer="158",
            rubric_steps=[
                {"step": "Reverse AP or find total number of terms n", "marks": 1.0},
                {"step": "Apply formula a + (n - 1)d", "marks": 1.0},
                {"step": "Final answer calculation 158", "marks": 1.0}
            ],
            source="CBSE Board 2020",
            topic_id=top3.id,
            subtopic_id=None
        )
        db.add(q3)

        db.commit()
        console.print("[bold green]Database successfully initialized and seeded![/bold green]\n")

        # Display Data Table Verification
        table = Table(title="Question Bank Sample Preview")
        table.add_column("ID", justify="center")
        table.add_column("Type", justify="center")
        table.add_column("Marks", justify="center")
        table.add_column("Difficulty", justify="center")
        table.add_column("Question")

        for q in db.query(Question).all():
            table.add_row(str(q.id), q.question_type.value, str(q.marks), q.difficulty.value, q.question_text[:50] + "...")

        console.print(table)

    except Exception as e:
        db.rollback()
        console.print(f"[bold red]Error during initialization:[/bold red] {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_database()
