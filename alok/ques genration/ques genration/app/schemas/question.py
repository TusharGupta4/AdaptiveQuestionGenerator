from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.models.question import QuestionType, DifficultyLevel

class OptionResponse(BaseModel):
    id: int
    option_label: str
    option_text: str
    is_correct: int

    model_config = ConfigDict(from_attributes=True)

class OptionCreate(BaseModel):
    option_label: str
    option_text: str
    is_correct: int = 0

class QuestionResponse(BaseModel):
    id: int
    question_text: str
    question_type: QuestionType
    marks: float
    difficulty: DifficultyLevel
    expected_answer: Optional[str]
    rubric_steps: Optional[List[Dict[str, Any]]]
    source: Optional[str]
    topic_id: int
    subtopic_id: Optional[int]
    options: List[OptionResponse] = []

    model_config = ConfigDict(from_attributes=True)

class QuestionCreate(BaseModel):
    question_text: str
    question_type: QuestionType
    marks: float
    difficulty: DifficultyLevel
    expected_answer: Optional[str] = None
    rubric_steps: Optional[List[Dict[str, Any]]] = None
    source: Optional[str] = "Manual Entry"
    topic_id: int
    subtopic_id: Optional[int] = None
    options: Optional[List[OptionCreate]] = None