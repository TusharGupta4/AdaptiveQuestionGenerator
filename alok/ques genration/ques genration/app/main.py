from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_v1_router

# Ensure tables are present
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Adaptive Exam Engine — Modular Question Bank, Paper Gen & Evaluation API",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 router
app.include_router(api_v1_router)

from app.core.supabase import check_supabase_connection

@app.get("/", tags=["Health Check"])
def root():
    return {
        "status": "online",
        "service": settings.APP_NAME,
        "docs_url": "/docs"
    }

@app.get("/supabase/status", tags=["Supabase Cloud"])
def supabase_status():
    return check_supabase_connection()