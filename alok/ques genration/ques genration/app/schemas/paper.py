from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator
from app.models.question import QuestionType, DifficultyLevel

class SectionRule(BaseModel):
    section_name: str = Field(description="e.g. 'Section A - MCQs'")
    question_type: QuestionType
    marks_per_question: float
    question_count: int
    allowed_difficulty: Optional[List[DifficultyLevel]] = None

class CustomPaperRequest(BaseModel):
    title: str = "Class 10 Practice Exam"
    subject_id: int
    total_marks: float
    duration_minutes: int = 45
    sections: List[SectionRule]
    chapter_ids: Optional[List[int]] = None  # None means all chapters included

    @model_validator(mode="after")
    def validate_total_marks_constraint(self):
        calculated_total = sum(s.marks_per_question * s.question_count for s in self.sections)
        if abs(calculated_total - self.total_marks) > 0.01:
            raise ValueError(
                f"Constraint Violation: Sections total ({calculated_total} marks) "
                f"does not match requested total_marks ({self.total_marks} marks)."
            )
        return self

class StandardPaperRequest(BaseModel):
    subject_id: int
    pattern_name: str = "QUICK_TEST_10"  # or "MID_TERM_20"

class PaperQuestionDetail(BaseModel):
    question_number: int
    section_name: str
    question_id: int
    question_text: str
    question_type: str
    marks: float
    difficulty: str
    options: Optional[List[Dict[str, Any]]] = None

class GeneratedPaperResponse(BaseModel):
    paper_id: int
    title: str
    subject_name: str
    total_marks: float
    duration_minutes: int
    sections: Dict[str, List[PaperQuestionDetail]]
    total_questions: int