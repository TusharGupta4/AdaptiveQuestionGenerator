import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.submission import SubmissionResponse
from app.services.submission_service import SubmissionService

router = APIRouter(prefix="/submissions", tags=["Student Submissions & OCR"])

SUBMISSION_DIR = Path("data/submissions")
SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload", response_model=SubmissionResponse)
def upload_student_answer_sheet(
    paper_id: int = Form(...),
    roll_number: str = Form(...),
    student_name: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload student's written/typed answer sheet, run OCR, and segment per question.
    """
    dest_path = SUBMISSION_DIR / f"{roll_number}_paper_{paper_id}_{file.filename}"
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = SubmissionService(db)
    return service.process_submission(
        paper_id=paper_id,
        student_roll=roll_number,
        student_name=student_name,
        file_path=str(dest_path)
    )