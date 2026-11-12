import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/ingest", tags=["Ingestion Pipeline"])

UPLOAD_DIR = Path("data/sample_inputs")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload")
def upload_and_ingest_paper(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a PDF or TXT paper and auto-extract & save questions into Question Bank.
    """
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".txt", ".pdf", ".md"]:
        raise HTTPException(status_code=400, detail="Only .txt, .pdf, and .md files supported")

    dest_path = UPLOAD_DIR / file.filename
    with open(dest_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    service = IngestionService(db)
    count = service.ingest_file(str(dest_path))

    return {
        "status": "success",
        "filename": file.filename,
        "questions_ingested": count
    }