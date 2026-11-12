from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.profile import StudentKnowledgeProfileResponse
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Student Knowledge Profile"])

@router.get("/student/{student_id}/profile", response_model=StudentKnowledgeProfileResponse)
def get_student_knowledge_profile(student_id: int, db: Session = Depends(get_db)):
    """
    Get student's mastery profile: strong/weak topics, accuracy, and AI recommendations.
    """
    service = AnalyticsService(db)
    return service.generate_student_profile(student_id)