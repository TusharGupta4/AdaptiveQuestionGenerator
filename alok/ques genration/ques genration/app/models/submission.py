from datetime import datetime
import enum
from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base

class SubmissionStatus(str, enum.Enum):
    PENDING_EVALUATION = "PENDING_EVALUATION"
    EVALUATED = "EVALUATED"

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    roll_number = Column(String(50), unique=True, nullable=False)
    grade = Column(String(20), default="Class 10")

    submissions = relationship("StudentSubmission", back_populates="student", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Student(name='{self.name}', roll='{self.roll_number}')>"


class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    paper_id = Column(Integer, ForeignKey("generated_papers.id"), nullable=False)
    file_path = Column(String(250), nullable=True)
    raw_ocr_text = Column(Text, nullable=True)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.PENDING_EVALUATION)
    total_score = Column(Float, nullable=True)  # Populated after Stage 6 evaluation
    submitted_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    student = relationship("Student", back_populates="submissions")
    paper = relationship("GeneratedPaper")
    answers = relationship("StudentAnswer", back_populates="submission", cascade="all, delete-orphan")


class StudentAnswer(Base):
    """Stores segmented student answer mapped to the exact paper question"""
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("student_submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    question_number = Column(Integer, nullable=False)  # 1, 2, 3...
    student_answer_text = Column(Text, nullable=False)

    # Evaluation fields (will be populated in Stage 6)
    marks_awarded = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    step_scores = Column(Text, nullable=True)  # JSON string

    submission = relationship("StudentSubmission", back_populates="answers")
    question = relationship("Question")