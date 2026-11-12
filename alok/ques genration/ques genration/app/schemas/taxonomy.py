from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class SubtopicResponse(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)

class TopicResponse(BaseModel):
    id: int
    name: str
    subtopics: List[SubtopicResponse] = []

    model_config = ConfigDict(from_attributes=True)

class ChapterResponse(BaseModel):
    id: int
    name: str
    chapter_number: Optional[int] = None
    topics: List[TopicResponse] = []

    model_config = ConfigDict(from_attributes=True)

class SubjectResponse(BaseModel):
    id: int
    name: str
    grade: str
    board: str
    chapters: List[ChapterResponse] = []

    model_config = ConfigDict(from_attributes=True)