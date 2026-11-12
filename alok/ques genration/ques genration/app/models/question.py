import enum
from sqlalchemy import Column, Integer, String, Text, Float, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.core.database import Base

class QuestionType(str, enum.Enum):
    MCQ = "MCQ"
    SHORT = "SHORT"
    LONG = "LONG"
    NUMERICAL = "NUMERICAL"

class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False, default=QuestionType.SHORT)
    marks = Column(Float, nullable=False)
    difficulty = Column(Enum(DifficultyLevel), nullable=False, default=DifficultyLevel.MEDIUM)

    # Expected Answer & Step-by-Step Rubrics
    expected_answer = Column(Text, nullable=True)
    rubric_steps = Column(JSON, nullable=True)  
    # e.g.: [{"step": "Formula written", "marks": 1.0}, {"step": "Correct calculation", "marks": 2.0}]

    source = Column(String(150), nullable=True)  # e.g. "CBSE Board 2023", "NCERT Exemplar"

    # Hierarchy Relations
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)
    subtopic_id = Column(Integer, ForeignKey("subtopics.id"), nullable=True)

    topic = relationship("Topic", back_populates="questions")
    subtopic = relationship("Subtopic", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Question(id={self.id}, type='{self.question_type}', marks={self.marks})>"


class QuestionOption(Base):
    """MCQ ke options (A, B, C, D) ke liye"""
    __tablename__ = "question_options"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    option_label = Column(String(5), nullable=False)  # 'A', 'B', 'C', 'D'
    option_text = Column(Text, nullable=False)
    is_correct = Column(Integer, default=0)  # 1 for correct, 0 for incorrect

    question = relationship("Question", back_populates="options")