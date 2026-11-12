from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class GeneratedPaper(Base):
    __tablename__ = "generated_papers"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    total_marks = Column(Float, nullable=False)
    duration_minutes = Column(Integer, default=60)
    blueprint = Column(JSON, nullable=True)  # Stored rules/config used to generate this
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    subject = relationship("Subject")
    paper_questions = relationship("PaperQuestion", back_populates="paper", cascade="all, delete-orphan", order_by="PaperQuestion.question_number")

    def __repr__(self):
        return f"<GeneratedPaper(id={self.id}, title='{self.title}', marks={self.total_marks})>"


class PaperQuestion(Base):
    """Maps which questions were assigned to which paper and in what section/order"""
    __tablename__ = "paper_questions"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("generated_papers.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    section_name = Column(String(50), nullable=False)  # e.g., "Section A", "Section B"
    question_number = Column(Integer, nullable=False)  # 1, 2, 3, 4...

    paper = relationship("GeneratedPaper", back_populates="paper_questions")
    question = relationship("Question")