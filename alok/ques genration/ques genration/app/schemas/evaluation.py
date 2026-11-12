from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class StepEvaluationResult(BaseModel):
    step_description: str
    max_marks: float
    marks_awarded: float
    is_satisfied: bool
    reasoning: str

class AnswerEvaluationResult(BaseModel):
    question_number: int
    question_id: int
    question_type: str
    max_marks: float
    marks_awarded: float
    feedback: str
    step_evaluations: List[StepEvaluationResult] = []

class SubmissionEvaluationReport(BaseModel):
    submission_id: int
    student_name: str
    roll_number: str
    paper_title: str
    total_paper_marks: float
    total_score_obtained: float
    percentage: float
    status: str
    detailed_answers: List[AnswerEvaluationResult]

    model_config = ConfigDict(from_attributes=True)