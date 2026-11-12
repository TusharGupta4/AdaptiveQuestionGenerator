from sqlalchemy.orm import Session
from app.services.pdf_extractor import DocumentExtractor
from app.services.question_structurer import QuestionStructurer
from app.services.taxonomy_matcher import TaxonomyMatcher
from app.models.question import Question, QuestionOption, QuestionType, DifficultyLevel

class IngestionService:
    def __init__(self, db: Session):
        self.db = db
        self.matcher = TaxonomyMatcher(db)

    def ingest_file(self, file_path: str) -> int:
        """Extract text from a PDF or text file and ingest questions."""
        raw_text = DocumentExtractor.extract_text_from_file(file_path)
        return self.ingest_raw_text(raw_text, source=f"Ingested from {file_path}")

    def ingest_raw_text(self, raw_text: str, source: str = "Direct Ingestion") -> int:
        """Parse raw text string and ingest extracted questions."""
        parsed_paper = QuestionStructurer.parse_paper(raw_text)
        return self.ingest_parsed_paper(parsed_paper, source=source)

    def ingest_parsed_paper(self, parsed_paper, source: str = "Direct Ingestion") -> int:
        """Persist structured ExtractedPaper model questions to database with taxonomy matching."""
        saved_count = 0
        for eq in parsed_paper.questions:
            topic_id, subtopic_id = self.matcher.match_topic_and_subtopic(
                chapter_name=eq.suggested_chapter,
                topic_name=eq.suggested_topic,
                subtopic_name=eq.suggested_subtopic
            )

            # Map Enums safely
            q_type = QuestionType[eq.question_type] if eq.question_type in QuestionType.__members__ else QuestionType.SHORT
            difficulty = DifficultyLevel[eq.difficulty] if eq.difficulty in DifficultyLevel.__members__ else DifficultyLevel.MEDIUM

            db_question = Question(
                question_text=eq.question_text,
                question_type=q_type,
                marks=eq.marks,
                difficulty=difficulty,
                expected_answer=eq.expected_answer,
                rubric_steps=eq.rubric_steps,
                source=source,
                topic_id=topic_id,
                subtopic_id=subtopic_id
            )
            self.db.add(db_question)
            self.db.flush()

            # If it's an MCQ, insert options
            if eq.options:
                for opt in eq.options:
                    db_opt = QuestionOption(
                        question_id=db_question.id,
                        option_label=opt.label,
                        option_text=opt.text,
                        is_correct=1 if opt.is_correct else 0
                    )
                    self.db.add(db_opt)

            saved_count += 1

        self.db.commit()
        return saved_count