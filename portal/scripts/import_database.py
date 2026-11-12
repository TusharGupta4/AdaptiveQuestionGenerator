import json
import sys
from pathlib import Path
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import engine, Base, init_db

TABLE_ORDER = [
    "boards",
    "academic_classes",
    "academic_streams",
    "subjects",
    "chapters",
    "topics",
    "questions",
    "examination_blueprints",
    "topic_weightages",
    "student_profiles",
    "generated_papers",
    "paper_questions",
    "student_submissions",
    "student_answers",
    "student_topic_mastery"
]

def import_data(dump_path: str = None):
    if not dump_path:
        dump_path = BASE_DIR / "data" / "database_dump.json"
    else:
        dump_path = Path(dump_path)

    if not dump_path.exists():
        print(f"Error: Dump file not found at: {dump_path}")
        print("Please run 'python portal/scripts/export_database.py' first or verify 'data/database_dump.json' exists.")
        sys.exit(1)

    print("============================================================")
    print("IMPORTING COLLEGEPUR DATABASE FROM PORTABLE DUMP")
    print(f"Source: {dump_path}")
    print(f"Target Database: {engine.url}")
    print("============================================================")

    # 1. Initialize schema
    init_db()

    with open(dump_path, "r", encoding="utf-8") as f:
        dump_data = json.load(f)

    tables_data = dump_data.get("tables", {})

    with engine.connect() as conn:
        # Disable foreign key checks for Postgres / SQLite during bulk import
        is_postgres = "postgres" in str(engine.url).lower()
        if is_postgres:
            conn.execute(text("SET session_replication_role = 'replica';"))

        for tbl in TABLE_ORDER:
            rows = tables_data.get(tbl, [])
            if not rows:
                continue

            # Clear existing table data to prevent duplicate primary keys
            conn.execute(text(f"DELETE FROM {tbl};"))

            cols = list(rows[0].keys())
            col_names = ", ".join(cols)
            placeholders = ", ".join([f":{c}" for c in cols])

            stmt = text(f"INSERT INTO {tbl} ({col_names}) VALUES ({placeholders});")

            # Clean rows: convert dict/list in JSON columns to JSON strings if needed
            cleaned_rows = []
            for r in rows:
                c_row = {}
                for k, v in r.items():
                    if isinstance(v, (dict, list)):
                        c_row[k] = json.dumps(v)
                    else:
                        c_row[k] = v
                cleaned_rows.append(c_row)

            # Insert in chunks of 500
            chunk_size = 500
            for i in range(0, len(cleaned_rows), chunk_size):
                chunk = cleaned_rows[i:i + chunk_size]
                conn.execute(stmt, chunk)

            print(f"  [✔] Imported '{tbl}': {len(rows)} records")

        if is_postgres:
            conn.execute(text("SET session_replication_role = 'origin';"))

        # Commit transaction
        conn.commit()

    print("\n============================================================")
    print("DATABASE IMPORT COMPLETED SUCCESSFULLY!")
    print(f"All {len(TABLE_ORDER)} tables and questions are now live in the database.")
    print("You can launch the portal anytime using: streamlit run portal/app.py")
    print("============================================================")

if __name__ == "__main__":
    arg_path = sys.argv[1] if len(sys.argv) > 1 else None
    import_data(arg_path)
