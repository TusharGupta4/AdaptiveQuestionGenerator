from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.adaptive import AdaptivePaperRequest, AdaptivePaperResponse
from app.services.adaptive_engine import AdaptivePaperEngine

router = APIRouter(prefix="/adaptive", tags=["Adaptive Paper Generation"])

@router.post("/generate", response_model=AdaptivePaperResponse)
def generate_adaptive_exam(req: AdaptivePaperRequest, db: Session = Depends(get_db)):
    """
    Generate personalized exam dynamically adapting to student's weak topics & mastery profile.
    """
    engine = AdaptivePaperEngine(db)
    return engine.generate_adaptive_paper(req)