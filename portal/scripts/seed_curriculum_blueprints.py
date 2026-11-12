import psycopg2
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.curriculum_weightages import CURRICULUM_REGISTRY

def seed_curriculum():
    conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='tushar@7744', dbname='collegepur_db')
    cur = conn.cursor()

    print("============================================================")
    print("SEEDING OFFICIAL BOARD PATTERNS & CHAPTER WEIGHTAGES")
    print("============================================================")

    # Cache boards, classes, subjects
    cur.execute("SELECT code, id FROM boards;")
    boards = dict(cur.fetchall())

    cur.execute("SELECT code, id FROM academic_classes;")
    classes = dict(cur.fetchall())

    for (b_code, c_code, s_name), spec in CURRICULUM_REGISTRY.items():
        if b_code not in boards or c_code not in classes:
            print(f"Skipping unknown board/class: {b_code} {c_code}")
            continue

        b_id = boards[b_code]
        c_id = classes[c_code]

        # 1. Get or create subject
        s_code = f"{b_code}{c_code}_{s_name[:4].upper()}"
        cur.execute("SELECT id FROM subjects WHERE board_id = %s AND class_id = %s AND name = %s;", (b_id, c_id, s_name))
        s_row = cur.fetchone()
        if not s_row:
            cur.execute("""
                INSERT INTO subjects (board_id, class_id, name, code)
                VALUES (%s, %s, %s, %s) RETURNING id;
            """, (b_id, c_id, s_name, s_code))
            s_id = cur.fetchone()[0]
        else:
            s_id = s_row[0]

        # 2. Get or create Blueprint
        cur.execute("SELECT id FROM examination_blueprints WHERE board_id = %s AND class_id = %s AND subject_id = %s AND title = %s;", (b_id, c_id, s_id, spec["title"]))
        bp_row = cur.fetchone()
        
        struct_cfg = {
            "sections": spec["sections"],
            "difficulty_target": spec["difficulty_target"],
            "unit_weightages": {k: v["weightage_percent"] for k, v in spec["weightages"].items()}
        }

        if not bp_row:
            cur.execute("""
                INSERT INTO examination_blueprints (board_id, class_id, subject_id, title, total_marks, duration_minutes, is_active, structure_config)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;
            """, (b_id, c_id, s_id, spec["title"], spec["total_marks"], spec["duration_minutes"], True, json.dumps(struct_cfg)))
            bp_id = cur.fetchone()[0]
            print(f"  [+] Created Blueprint: {spec['title']} (ID: {bp_id})")
        else:
            bp_id = bp_row[0]
            cur.execute("""
                UPDATE examination_blueprints 
                SET structure_config = %s, total_marks = %s, duration_minutes = %s
                WHERE id = %s;
            """, (json.dumps(struct_cfg), spec["total_marks"], spec["duration_minutes"], bp_id))

        # 3. Seed Chapters & Topic Weightages
        for unit_name, u_spec in spec["weightages"].items():
            pct = u_spec["weightage_percent"]
            t_marks = u_spec["target_marks"]
            ch_list = u_spec.get("chapters", [unit_name])

            for ch_name in ch_list:
                # Find or insert chapter
                cur.execute("SELECT id FROM chapters WHERE subject_id = %s AND name ILIKE %s;", (s_id, ch_name))
                ch_row = cur.fetchone()
                if not ch_row:
                    cur.execute("""
                        INSERT INTO chapters (subject_id, name)
                        VALUES (%s, %s) RETURNING id;
                    """, (s_id, ch_name))
                    ch_id = cur.fetchone()[0]
                else:
                    ch_id = ch_row[0]

                # Insert topic weightage entry
                cur.execute("""
                    SELECT id FROM topic_weightages 
                    WHERE blueprint_id = %s AND chapter_id = %s;
                """, (bp_id, ch_id))
                if not cur.fetchone():
                    # Split unit target marks across its chapters
                    ch_share_marks = round(t_marks / max(1, len(ch_list)), 1)
                    ch_share_pct = round(pct / max(1, len(ch_list)), 2)
                    cur.execute("""
                        INSERT INTO topic_weightages (blueprint_id, chapter_id, weightage_percent, min_marks, max_marks, is_official)
                        VALUES (%s, %s, %s, %s, %s, %s);
                    """, (bp_id, ch_id, ch_share_pct, max(1.0, ch_share_marks - 2.0), ch_share_marks + 3.0, True))

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM examination_blueprints;")
    bp_cnt = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM topic_weightages;")
    tw_cnt = cur.fetchone()[0]
    print(f"\nCompleted! Active Blueprints: {bp_cnt} | Total Chapter Weightages: {tw_cnt}")
    conn.close()

if __name__ == "__main__":
    seed_curriculum()
