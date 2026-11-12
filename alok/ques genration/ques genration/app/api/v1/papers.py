from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.paper import CustomPaperRequest, StandardPaperRequest, GeneratedPaperResponse
from app.services.paper_generator import PaperGeneratorEngine
from app.services.paper_renderer import PaperRenderer

router = APIRouter(prefix="/papers", tags=["Paper Generation Engine"])

@router.post("/generate/custom", response_model=GeneratedPaperResponse)
def generate_custom_paper(req: CustomPaperRequest, db: Session = Depends(get_db)):
    """
    Generate paper with exact custom marks constraint & section distribution.
    """
    engine = PaperGeneratorEngine(db)
    result = engine.generate_custom_paper(req)
    # Render printable HTML file
    PaperRenderer.render_to_html(result)
    return result

@router.post("/generate/standard", response_model=GeneratedPaperResponse)
def generate_standard_paper(req: StandardPaperRequest, db: Session = Depends(get_db)):
    """
    Generate paper based on predefined standard exam blueprint.
    """
    engine = PaperGeneratorEngine(db)
    result = engine.generate_standard_paper(req.subject_id, req.pattern_name)
    PaperRenderer.render_to_html(result)
    return result