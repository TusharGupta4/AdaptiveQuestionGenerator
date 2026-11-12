from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.evaluation import SubmissionEvaluationReport
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluate", tags=["Evaluation Engine"])

@router.post("/{submission_id}", response_model=SubmissionEvaluationReport)
def evaluate_submission_endpoint(submission_id: int, db: Session = Depends(get_db)):
    """
    Run multi-criteria rubric evaluation with partial credit and step-by-step reasoning.
    """
    service = EvaluationService(db)
    return service.evaluate_submission(submission_id)

@router.get("/{submission_id}/report", response_model=SubmissionEvaluationReport)
def get_evaluation_report(submission_id: int, db: Session = Depends(get_db)):
    """
    Get the evaluated scorecard and feedback report for a submission.
    """
    service = EvaluationService(db)
    return service.evaluate_submission(submission_id)