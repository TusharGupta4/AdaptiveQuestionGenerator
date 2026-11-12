from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    grade = Column(String(20), nullable=False)  # e.g., "Class 10", "Class 12"
    board = Column(String(50), default="CBSE")  # e.g., "CBSE", "ICSE", "State"

    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Subject(name='{self.name}', grade='{self.grade}')>"


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    chapter_number = Column(Integer, nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    subject = relationship("Subject", back_populates="chapters")
    topics = relationship("Topic", back_populates="chapter", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Chapter(name='{self.name}', num={self.chapter_number})>"


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)

    chapter = relationship("Chapter", back_populates="topics")
    subtopics = relationship("Subtopic", back_populates="topic", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="topic")

    def __repr__(self):
        return f"<Topic(name='{self.name}')>"


class Subtopic(Base):
    __tablename__ = "subtopics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=False)

    topic = relationship("Topic", back_populates="subtopics")
    questions = relationship("Question", back_populates="subtopic")

    def __repr__(self):
        return f"<Subtopic(name='{self.name}')>"