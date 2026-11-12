from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from datetime import datetime

class StudentAnswerDetail(BaseModel):
    question_number: int
    question_id: int
    question_text: str
    student_answer_text: str
    marks_allocated: float

class SubmissionResponse(BaseModel):
    submission_id: int
    student_name: str
    roll_number: str
    paper_id: int
    paper_title: str
    total_answers_extracted: int
    status: str
    answers: List[StudentAnswerDetail]
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)