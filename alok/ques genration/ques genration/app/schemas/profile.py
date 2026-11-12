from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.models.profile import MasteryStatus

class TopicMasteryDetail(BaseModel):
    topic_id: int
    topic_name: str
    chapter_name: str
    marks_obtained: float
    marks_possible: float
    accuracy_percentage: float
    status: MasteryStatus

    model_config = ConfigDict(from_attributes=True)

class SubtopicMasteryDetail(BaseModel):
    subtopic_id: int
    subtopic_name: str
    topic_name: str
    marks_obtained: float
    marks_possible: float
    accuracy_percentage: float
    status: MasteryStatus

    model_config = ConfigDict(from_attributes=True)

class StudentKnowledgeProfileResponse(BaseModel):
    student_id: int
    student_name: str
    roll_number: str
    overall_accuracy: float
    total_questions_attempted: int
    
    # Categorized lists for Person 2 (Adaptive Engine)
    strong_topics: List[str]
    moderate_topics: List[str]
    weak_topics: List[str]
    weak_subtopics: List[str]

    # Full details
    topic_performance: List[TopicMasteryDetail]
    recommendations: List[str]

    model_config = ConfigDict(from_attributes=True)