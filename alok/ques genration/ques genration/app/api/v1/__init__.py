from fastapi import APIRouter
from app.api.v1.syllabus import router as syllabus_router
from app.api.v1.questions import router as questions_router
from app.api.v1.ingestion import router as ingestion_router
from app.api.v1.papers import router as papers_router
from app.api.v1.submissions import router as submissions_router
from app.api.v1.evaluation import router as evaluation_router
from app.api.v1.analytics import router as analytics_router
from app.api.v1.adaptive import router as adaptive_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(syllabus_router)
api_v1_router.include_router(questions_router)
api_v1_router.include_router(ingestion_router)
api_v1_router.include_router(papers_router)
api_v1_router.include_router(submissions_router)
api_v1_router.include_router(evaluation_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(adaptive_router)