from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.taxonomy import Subject, Chapter, Topic
from app.schemas.taxonomy import SubjectResponse, ChapterResponse, TopicResponse

router = APIRouter(prefix="/syllabus", tags=["Syllabus & Hierarchy"])

@router.get("/subjects", response_model=List[SubjectResponse])
def get_all_subjects(db: Session = Depends(get_db)):
    """Pure syllabus tree: Subjects -> Chapters -> Topics -> Subtopics"""
    return db.query(Subject).all()

@router.get("/subjects/{subject_id}", response_model=SubjectResponse)
def get_subject_by_id(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    return subject

@router.get("/chapters/{chapter_id}/topics", response_model=List[TopicResponse])
def get_topics_for_chapter(chapter_id: int, db: Session = Depends(get_db)):
    topics = db.query(Topic).filter(Topic.chapter_id == chapter_id).all()
    return topics