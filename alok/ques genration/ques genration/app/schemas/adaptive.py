from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.paper import GeneratedPaperResponse

class AdaptivePaperRequest(BaseModel):
    student_id: int
    title: Optional[str] = "Personalized Adaptive Diagnostic Exam"
    total_marks: float = Field(default=6.0, description="Total paper marks constraint")
    duration_minutes: int = Field(default=30)
    focus_mode: str = Field(default="REMEDIAL", description="REMEDIAL (focus on weak topics) or CHALLENGE")

class AdaptiveTopicAllocation(BaseModel):
    topic_name: str
    status: str
    allocated_marks: float
    questions_count: int

class AdaptivePaperResponse(BaseModel):
    paper_details: GeneratedPaperResponse
    student_id: int
    student_name: str
    remedial_focus_topics: List[str]
    topic_allocation_summary: List[AdaptiveTopicAllocation]
    pedagogical_rationale: str