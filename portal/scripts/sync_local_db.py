import sys
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.config import DEFAULT_PG_URL
from portal.core.database import (
    Base, Board, AcademicClass, AcademicStream, Subject, Chapter, Topic,
    Question, ExaminationBlueprint, TopicWeightage, StudentProfile
)

def sync_to_sqlite(sqlite_path=None):
    if not sqlite_path:
        data_dir = BASE_DIR / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        sqlite_path = data_dir / "exam_engine.db"
    
    print("=" * 60)
    print("SYNCING MASTER POSTGRESQL DATABASE -> LOCAL SQLITE DATABASE")
    print(f"Target SQLite DB: {sqlite_path}")
    print("=" * 60)

    # 1. Connect to PostgreSQL Master
    pg_engine = create_engine(DEFAULT_PG_URL)
    PgSession = sessionmaker(bind=pg_engine)
    pg_db = PgSession()

    # 2. Connect to Local SQLite
    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(sqlite_url)
    Base.metadata.create_all(bind=sqlite_engine)
    SqliteSession = sessionmaker(bind=sqlite_engine)
    sqlite_db = SqliteSession()

    tables = [
        Board, AcademicClass, AcademicStream, Subject,
        Chapter, Topic, Question, ExaminationBlueprint,
        TopicWeightage, StudentProfile
    ]

    try:
        for model in tables:
            m_name = model.__tablename__
            rows = pg_db.query(model).all()
            print(f"Syncing table '{m_name}' ({len(rows)} records)...")
            
            # Clear existing rows in target table to avoid duplicates
            sqlite_db.query(model).delete()
            
            for r in rows:
                # Replicate attributes into new instance
                data = {c.name: getattr(r, c.name) for c in model.__table__.columns}
                sqlite_db.add(model(**data))
            
            sqlite_db.commit()

        print("\n" + "=" * 60)
        print("SYNC COMPLETE!")
        print(f"Your teammates can now run the portal completely offline using:")
        print(f"DATABASE_URL=sqlite:///./data/exam_engine.db")
        print("=" * 60)

    except Exception as e:
        sqlite_db.rollback()
        print(f"[ERROR] Sync failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        pg_db.close()
        sqlite_db.close()

if __name__ == "__main__":
    sync_to_sqlite()
