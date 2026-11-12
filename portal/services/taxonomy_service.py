from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from portal.core.database import Board, AcademicClass, Subject, Chapter, Topic, Question, StudentProfile

class TaxonomyService:
    def __init__(self, db: Session):
        self.db = db

    def get_boards(self) -> List[Board]:
        return self.db.query(Board).all()

    def get_classes(self) -> List[AcademicClass]:
        return self.db.query(AcademicClass).all()

    def get_subjects(self, board_id: Optional[int] = None, class_id: Optional[int] = None) -> List[Subject]:
        q = self.db.query(Subject)
        if board_id:
            q = q.filter(Subject.board_id == board_id)
        if class_id:
            q = q.filter(Subject.class_id == class_id)
        return q.all()

    def get_chapters(self, subject_id: int) -> List[Chapter]:
        return self.db.query(Chapter).filter(Chapter.subject_id == subject_id).all()

    def get_topics(self, chapter_id: int) -> List[Topic]:
        return self.db.query(Topic).filter(Topic.chapter_id == chapter_id).all()

    def get_or_create_student(self, email: str, full_name: str, board_id: int, class_id: int) -> StudentProfile:
        student = self.db.query(StudentProfile).filter(StudentProfile.email == email).first()
        if not student:
            student = StudentProfile(
                email=email,
                full_name=full_name,
                board_id=board_id,
                class_id=class_id
            )
            self.db.add(student)
            self.db.commit()
            self.db.refresh(student)
        return student
