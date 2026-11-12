from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Normalize database URL (e.g., Supabase postgres:// -> postgresql+psycopg2://)
"""db_url = settings.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

# SQLite connection args (check_same_thread=False for FastAPI multi-threading)
connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}

engine_kwargs = {
    "connect_args": connect_args,
    "echo": False
}

# If PostgreSQL, enable pool pre-ping to handle disconnected connections gracefully
if db_url.startswith("postgresql"):
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# PostgreSQL ke liye clean engine args
if settings.DATABASE_URL.startswith("sqlite"):
    engine_kwargs = {"connect_args": {"check_same_thread": False}}
else:
    # Supabase PostgreSQL configuration
    engine_kwargs = {
        "pool_pre_ping": True,       # Checks connection validity before executing queries
        "pool_recycle": 300,         # Recycles idle connections every 5 mins
        "pool_size": 10,
        "max_overflow": 20
    }

engine = create_engine(settings.DATABASE_URL, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()