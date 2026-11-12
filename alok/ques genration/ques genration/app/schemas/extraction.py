from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ExtractedOption(BaseModel):
    label: str = Field(description="Option label like A, B, C, D")
    text: str = Field(description="Content of the option")
    is_correct: bool = Field(default=False)

class ExtractedQuestion(BaseModel):
    question_text: str
    question_type: str = Field(description="MCQ, SHORT, LONG, or NUMERICAL")
    marks: float
    difficulty: str = Field(description="EASY, MEDIUM, or HARD")
    expected_answer: Optional[str] = None
    rubric_steps: Optional[List[Dict[str, Any]]] = None
    suggested_chapter: str
    suggested_topic: str
    suggested_subtopic: Optional[str] = None
    options: Optional[List[ExtractedOption]] = None
    source: Optional[str] = "Imported Paper"

class ExtractedPaper(BaseModel):
    subject: str
    grade: str
    questions: List[ExtractedQuestion]