import json
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import engine

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

def default_serializer(obj):
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    if isinstance(obj, (Decimal,)):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def export_data():
    output_dir = BASE_DIR / "data"
    output_dir.mkdir(exist_ok=True, parents=True)
    json_path = output_dir / "database_dump.json"

    print("============================================================")
    print("EXPORTING COLLEGEPUR MASTER DATABASE TO PORTABLE DUMP")
    print("============================================================")

    dump_data = {
        "version": "1.0",
        "exported_at": datetime.utcnow().isoformat(),
        "tables": {}
    }

    total_records = 0
    with engine.connect() as conn:
        for tbl in TABLE_ORDER:
            res = conn.execute(text(f"SELECT * FROM {tbl};"))
            cols = res.keys()
            rows = [dict(zip(cols, row)) for row in res.fetchall()]
            dump_data["tables"][tbl] = rows
            count = len(rows)
            total_records += count
            print(f"  [+] Exported '{tbl}': {count} records")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dump_data, f, indent=2, default=default_serializer, ensure_ascii=False)

    size_mb = round(json_path.stat().st_size / (1024 * 1024), 2)
    print(f"\nSUCCESS! Master database exported to: {json_path}")
    print(f"Total Tables: {len(TABLE_ORDER)} | Total Records: {total_records} | Size: {size_mb} MB")
    print("============================================================")

if __name__ == "__main__":
    export_data()

