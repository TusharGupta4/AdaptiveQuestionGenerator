from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.question import Question, QuestionOption, QuestionType, DifficultyLevel
from app.models.taxonomy import Topic, Chapter
from app.schemas.question import QuestionResponse, QuestionCreate

router = APIRouter(prefix="/questions", tags=["Question Bank"])

@router.get("", response_model=List[QuestionResponse])
def get_questions(
    chapter_id: Optional[int] = Query(None, description="Filter by chapter ID"),
    topic_id: Optional[int] = Query(None, description="Filter by topic ID"),
    subtopic_id: Optional[int] = Query(None, description="Filter by subtopic ID"),
    question_type: Optional[QuestionType] = Query(None, description="MCQ, SHORT, LONG, NUMERICAL"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="EASY, MEDIUM, HARD"),
    min_marks: Optional[float] = Query(None, description="Minimum marks"),
    max_marks: Optional[float] = Query(None, description="Maximum marks"),
    search: Optional[str] = Query(None, description="Keyword search in question text"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Search and filter questions from the Question Bank with full criteria.
    """
    query = db.query(Question)

    if chapter_id:
        query = query.join(Topic, Question.topic_id == Topic.id)\
                     .filter(Topic.chapter_id == chapter_id)
    if topic_id:
        query = query.filter(Question.topic_id == topic_id)
    if subtopic_id:
        query = query.filter(Question.subtopic_id == subtopic_id)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    if difficulty:
        query = query.filter(Question.difficulty == difficulty)
    if min_marks is not None:
        query = query.filter(Question.marks >= min_marks)
    if max_marks is not None:
        query = query.filter(Question.marks <= max_marks)
    if search:
        query = query.filter(Question.question_text.ilike(f"%{search}%"))

    return query.offset(offset).limit(limit).all()

@router.get("/{question_id}", response_model=QuestionResponse)
def get_question_by_id(question_id: int, db: Session = Depends(get_db)):
    """Fetch a specific question with its options and rubric steps."""
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

@router.post("", response_model=QuestionResponse, status_code=201)
def create_question(payload: QuestionCreate, db: Session = Depends(get_db)):
    """Add a new question into the Question Bank manually."""
    question = Question(
        question_text=payload.question_text,
        question_type=payload.question_type,
        marks=payload.marks,
        difficulty=payload.difficulty,
        expected_answer=payload.expected_answer,
        rubric_steps=payload.rubric_steps,
        source=payload.source,
        topic_id=payload.topic_id,
        subtopic_id=payload.subtopic_id,
    )
    db.add(question)
    db.flush()

    if payload.options and payload.question_type == QuestionType.MCQ:
        for opt in payload.options:
            db_opt = QuestionOption(
                question_id=question.id,
                option_label=opt.option_label,
                option_text=opt.option_text,
                is_correct=opt.is_correct
            )
            db.add(db_opt)

    db.commit()
    db.refresh(question)
    return question