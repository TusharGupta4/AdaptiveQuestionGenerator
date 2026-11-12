import psycopg2
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

conn = psycopg2.connect(host='localhost', port=5432, user='postgres', password='tushar@7744', dbname='collegepur_db')
cur = conn.cursor()

# 1. Populate JEE chapter weightages
jee_weight_path = BASE_DIR / 'JEE-assessment-RAG' / 'jee_chapter_weightage.json'
if jee_weight_path.exists():
    with open(jee_weight_path, 'r', encoding='utf-8') as f:
        jee_data = json.load(f)
    
    cur.execute("SELECT id FROM examination_blueprints WHERE title LIKE '%JEE%';")
    jee_bp = cur.fetchone()
    jee_bp_id = jee_bp[0] if jee_bp else None

    inserted_count = 0
    for subj_name, classes in jee_data.items():
        for cls_name, chs in classes.items():
            for ch_name, pct_str in chs.items():
                pct = float(pct_str.replace('%', ''))
                cur.execute('SELECT id FROM chapters WHERE name = %s;', (ch_name,))
                ch_row = cur.fetchone()
                ch_id = ch_row[0] if ch_row else None
                if ch_id:
                    cur.execute('''
                        INSERT INTO topic_weightages (blueprint_id, chapter_id, weightage_percent, is_official)
                        VALUES (%s, %s, %s, %s);
                    ''', (jee_bp_id, ch_id, pct, True))
                    inserted_count += 1
    print(f'Populated {inserted_count} JEE topic weightages.')

# 2. CBSE 10 Math official unit weightages
cur.execute("SELECT id FROM examination_blueprints WHERE title LIKE '%CBSE Class 10 Standard Mathematics%';")
math_bp = cur.fetchone()
if math_bp:
    cbse_math_units = [
        ('Number Systems', 6.0, 7.5),
        ('Algebra', 20.0, 25.0),
        ('Coordinate Geometry', 6.0, 7.5),
        ('Geometry', 15.0, 18.75),
        ('Trigonometry', 12.0, 15.0),
        ('Mensuration', 10.0, 12.5),
        ('Statistics And Probability', 11.0, 13.75)
    ]
    cbse_count = 0
    for uname, mks, pct in cbse_math_units:
        cur.execute('SELECT id FROM chapters WHERE name ILIKE %s;', (f'%{uname}%',))
        ch_rows = cur.fetchall()
        for ch_row in ch_rows:
            cur.execute('''
                INSERT INTO topic_weightages (blueprint_id, chapter_id, weightage_percent, min_marks, max_marks, is_official)
                VALUES (%s, %s, %s, %s, %s, %s);
            ''', (math_bp[0], ch_row[0], pct, mks, mks, True))
            cbse_count += 1
    print(f'Populated {cbse_count} CBSE Class 10 Math unit weightages.')

conn.commit()
cur.execute('SELECT COUNT(*) FROM topic_weightages;')
print('Total topic_weightages in database:', cur.fetchone()[0])
conn.close()

