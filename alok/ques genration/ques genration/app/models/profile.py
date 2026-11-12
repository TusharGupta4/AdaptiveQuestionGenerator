from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class MasteryStatus(str, enum.Enum):
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"

class StudentTopicMastery(Base):
    __tablename__ = "student_topic_mastery"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)

    attempts_count = Column(Integer, default=0)
    marks_possible = Column(Float, default=0.0)
    marks_obtained = Column(Float, default=0.0)
    mastery_score = Column(Float, default=0.0)  # Percentage ratio 0.0 to 1.0
    status = Column(Enum(MasteryStatus), default=MasteryStatus.MODERATE)
    last_updated = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student")
    topic = relationship("Topic")
    subtopic = relationship("Subtopic")