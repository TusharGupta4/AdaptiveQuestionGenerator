import os
import sys
import json
import glob
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import (
    SessionLocal, init_db, Board, AcademicClass, AcademicStream,
    Subject, Chapter, Topic, Question, ExaminationBlueprint, TopicWeightage, StudentProfile
)

def run_seed():
    print("=" * 60)
    print("STARTING COMPLETE MASTER SEEDING OF COLLEGEPUR DATABASE")
    print("=" * 60)
    
    init_db()
    db = SessionLocal()
    
    try:
        # Clear previous questions and taxonomy to re-seed cleanly with exact names
        print("\n[0/8] Cleaning previous seed data for clean rebuild...")
        from portal.core.database import StudentAnswer, StudentSubmission, PaperQuestion, GeneratedPaper, StudentTopicMastery
        db.query(StudentAnswer).delete()
        db.query(StudentSubmission).delete()
        db.query(PaperQuestion).delete()
        db.query(GeneratedPaper).delete()
        db.query(StudentTopicMastery).delete()
        db.query(Question).delete()
        db.query(Topic).delete()
        db.query(Chapter).delete()
        db.commit()

        # 1. BOARDS
        print("\n[1/8] Verifying Educational Boards...")
        boards_data = [
            ("CBSE", "Central Board of Secondary Education"),
            ("ICSE", "Indian Certificate of Secondary Education"),
            ("ISC", "Indian School Certificate (Classes 11 & 12)"),
            ("JEE", "Joint Entrance Examination (Main & Advanced)")
        ]
        boards = {}
        for code, name in boards_data:
            b = db.query(Board).filter(Board.code == code).first()
            if not b:
                b = Board(code=code, name=name)
                db.add(b)
                db.flush()
            boards[code] = b
        db.commit()

        # 2. ACADEMIC CLASSES & STREAMS
        print("\n[2/8] Verifying Academic Classes & Streams...")
        classes_data = [
            ("Class 9", "9"),
            ("Class 10", "10"),
            ("Class 11", "11"),
            ("Class 12", "12"),
            ("Competitive (JEE)", "JEE")
        ]
        classes = {}
        for grade, code in classes_data:
            c = db.query(AcademicClass).filter(AcademicClass.code == code).first()
            if not c:
                c = AcademicClass(grade=grade, code=code)
                db.add(c)
                db.flush()
            classes[code] = c

        streams_data = ["General", "Science", "Commerce", "Humanities"]
        for sname in streams_data:
            if not db.query(AcademicStream).filter(AcademicStream.name == sname).first():
                db.add(AcademicStream(name=sname))
        db.commit()

        # Helpers
        subjects_cache = {}
        chapters_cache = {}
        topics_cache = {}
        id_to_name = {}

        def get_or_create_subject(board_code, class_code, subj_name, subj_code):
            key = (board_code, class_code, subj_code)
            if key in subjects_cache:
                return subjects_cache[key]
            
            b = boards[board_code]
            c = classes[class_code]
            s = db.query(Subject).filter(Subject.board_id == b.id, Subject.class_id == c.id, Subject.code == subj_code).first()
            if not s:
                s = Subject(board_id=b.id, class_id=c.id, name=subj_name, code=subj_code)
                db.add(s)
                db.flush()
            subjects_cache[key] = s
            return s

        def get_or_create_chapter(subject_obj, chapter_code, chapter_name):
            key = (subject_obj.id, chapter_name)
            if key in chapters_cache:
                return chapters_cache[key]
            
            ch = db.query(Chapter).filter(Chapter.subject_id == subject_obj.id, Chapter.name == chapter_name).first()
            if not ch:
                ch = Chapter(subject_id=subject_obj.id, chapter_code=chapter_code, name=chapter_name)
                db.add(ch)
                db.flush()
            chapters_cache[key] = ch
            return ch

        # 3. SEED PIYUSH'S CBSE 2026-27 SYLLABUS FILES (RECURSIVE TREE)
        print("\n[3/8] Ingesting Official CBSE 2026-27 Syllabi (Piyush Tree Walk)...")
        syllabus_files = glob.glob(str(BASE_DIR / "piyush" / "CBSE-9-10" / "data" / "syllabus" / "*.json"))
        
        for s_file in syllabus_files:
            fname = Path(s_file).name
            if "backup" in s_file: continue
            
            with open(s_file, "r", encoding="utf-8") as fp:
                s_data = json.load(fp)
            
            s_class_str = "9" if "class9" in fname else ("10" if "class10" in fname else "10")
            s_subj_raw = s_data.get("subject", "").lower()
            
            if "math" in s_subj_raw:
                subj_name, subj_code = "Mathematics", f"CBSE{s_class_str}_MATH"
            elif "science" in s_subj_raw and "social" not in s_subj_raw and "home" not in s_subj_raw:
                subj_name, subj_code = "Science", f"CBSE{s_class_str}_SCI"
            elif "social" in s_subj_raw:
                subj_name, subj_code = "Social Science", f"CBSE{s_class_str}_SST"
            elif "computer" in s_subj_raw:
                subj_name, subj_code = "Computer Applications", f"CBSE{s_class_str}_CA"
            elif "home" in s_subj_raw:
                subj_name, subj_code = "Home Science", f"CBSE{s_class_str}_HS"
            else:
                subj_name, subj_code = s_subj_raw.title(), f"CBSE{s_class_str}_{s_subj_raw[:4].upper()}"

            subj_obj = get_or_create_subject("CBSE", s_class_str, subj_name, subj_code)
            
            curriculum = s_data.get("curriculum", [])
            for top_node in curriculum:
                unit_name = top_node.get("name", "").title()
                unit_id = top_node.get("id")
                if unit_id: id_to_name[unit_id] = unit_name
                
                # If node has children, children are chapters
                children = top_node.get("children", [])
                if children:
                    for ch_node in children:
                        c_id = ch_node.get("id")
                        c_name = ch_node.get("name", "").title()
                        if c_id: id_to_name[c_id] = c_name
                        ch_obj = get_or_create_chapter(subj_obj, c_id, c_name)
                        
                        for t_node in ch_node.get("children", []):
                            t_id = t_node.get("id")
                            t_name = t_node.get("name", "").title()
                            if t_id: id_to_name[t_id] = t_name
                            tp = Topic(chapter_id=ch_obj.id, topic_code=t_id, name=t_name)
                            db.add(tp)
                else:
                    # Single level unit/chapter
                    ch_obj = get_or_create_chapter(subj_obj, unit_id, unit_name)

        db.commit()
        print(f"  CBSE Syllabi imported! Mapped {len(id_to_name)} canonical IDs across {len(chapters_cache)} chapters.")

        # 4. SEED JEE SYLLABUS & CHAPTERS
        print("\n[4/8] Ingesting JEE Chapter Weightages...")
        jee_weight_path = BASE_DIR / "JEE-assessment-RAG" / "jee_chapter_weightage.json"
        if jee_weight_path.exists():
            with open(jee_weight_path, "r", encoding="utf-8") as fp:
                jee_data = json.load(fp)
            
            jee_subj_map = {"Mathematics": "JEE_MATH", "Physics": "JEE_PHYS", "Chemistry": "JEE_CHEM"}
            for subj_name, classes_dict in jee_data.items():
                scode = jee_subj_map.get(subj_name, f"JEE_{subj_name[:4].upper()}")
                subj_obj = get_or_create_subject("JEE", "JEE", subj_name, scode)
                
                for cls_name, chapters_dict in classes_dict.items():
                    for ch_name, weight_str in chapters_dict.items():
                        get_or_create_chapter(subj_obj, None, ch_name)

            db.commit()
            print("  JEE Subjects & Chapters imported successfully!")

        # 5. SEED REKHA & PIYUSH'S 1,726 CBSE QUESTIONS WITH REAL CHAPTER NAMES
        print("\n[5/8] Ingesting 1,726 Classified CBSE Questions (Rekha + Piyush)...")
        qb_path = BASE_DIR / "rekha" / "CBSE_AI_Assessment" / "data" / "processed" / "clean_question_bank.csv"
        class_path = BASE_DIR / "piyush" / "CBSE-9-10" / "data" / "processed" / "classification_results.jsonl"
        
        df_qb = pd.read_csv(qb_path)
        class_lookup = {}
        with open(class_path, "r", encoding="utf-8") as fp:
            for line in fp:
                item = json.loads(line)
                qid = item.get("question_id")
                if qid: class_lookup[qid] = item

        cbse_inserted = 0
        for _, row in df_qb.iterrows():
            raw_qid = row.get("question_id")
            canon_id = f"CBSE_Q_{int(raw_qid):04d}" if str(raw_qid).isdigit() else f"CBSE_{raw_qid}"
            
            q_lookup_key = f"Q_{int(raw_qid):04d}" if str(raw_qid).isdigit() else str(raw_qid)
            class_info = class_lookup.get(q_lookup_key, {})
            
            cls_code = "9" if str(row.get("class")).lower() in ["class9", "9"] else "10"
            raw_subj = str(row.get("subject", "maths")).lower()
            if "math" in raw_subj:
                subj_name, subj_code = "Mathematics", f"CBSE{cls_code}_MATH"
            elif "science" in raw_subj and "social" not in raw_subj and "home" not in raw_subj:
                subj_name, subj_code = "Science", f"CBSE{cls_code}_SCI"
            elif "social" in raw_subj:
                subj_name, subj_code = "Social Science", f"CBSE{cls_code}_SST"
            elif "computer" in raw_subj:
                subj_name, subj_code = "Computer Applications", f"CBSE{cls_code}_CA"
            elif "home" in raw_subj:
                subj_name, subj_code = "Home Science", f"CBSE{cls_code}_HS"
            else:
                subj_name, subj_code = raw_subj.title(), f"CBSE{cls_code}_{raw_subj[:4].upper()}"

            subj_obj = get_or_create_subject("CBSE", cls_code, subj_name, subj_code)
            
            # Map chapter using Piyush's classified codes
            ch_code = class_info.get("chapter_id")
            unit_code = class_info.get("unit_id")
            
            ch_name = None
            if ch_code and ch_code in id_to_name:
                ch_name = id_to_name[ch_code]
            elif unit_code and unit_code in id_to_name:
                ch_name = id_to_name[unit_code]
            
            if not ch_name or str(ch_name).lower() == "nan":
                raw_topic = str(row.get("topic") or "")
                ch_name = raw_topic.title() if raw_topic and raw_topic.lower() != "nan" else f"{subj_name} Core Concepts"

            ch_obj = get_or_create_chapter(subj_obj, ch_code, ch_name)
            
            raw_opts = row.get("options")
            options_dict = {}
            if pd.notna(raw_opts) and str(raw_opts).strip() and str(raw_opts).lower() != "nan":
                opts_str = str(raw_opts)
                if "|" in opts_str:
                    parts = opts_str.split("|")
                    labels = ["A", "B", "C", "D", "E"]
                    for idx, p in enumerate(parts):
                        if idx < len(labels): options_dict[labels[idx]] = p.strip()
                else:
                    options_dict["A"] = opts_str.strip()

            q_type = str(row.get("question_type", "short_answer")).lower()
            if "mcq" in q_type: q_type = "mcq_single"
            elif "long" in q_type: q_type = "long_answer"
            elif "case" in q_type: q_type = "case_based"
            elif "numerical" in q_type: q_type = "numerical"
            else: q_type = "short_answer"

            marks = float(row.get("marks", 1.0)) if pd.notna(row.get("marks")) else 1.0
            diff = str(row.get("difficulty") or "Medium").title()
            if diff.lower() == "nan": diff = "Medium"

            q_entry = Question(
                canonical_id=canon_id,
                board_id=boards["CBSE"].id,
                class_id=classes[cls_code].id,
                subject_id=subj_obj.id,
                chapter_id=ch_obj.id,
                subject_name=subj_obj.name,
                chapter_name=ch_obj.name,
                topic_name=ch_obj.name,
                question_number=int(row.get("question_number", 0)) if pd.notna(row.get("question_number")) and str(row.get("question_number")).isdigit() else None,
                question_type=q_type,
                question_text=str(row.get("question_text_clean") or row.get("question_text")),
                options=options_dict if options_dict else None,
                correct_answer=str(row.get("correct_answer") or row.get("answer") or ""),
                solution=str(row.get("answer_explanation") or ""),
                marks=marks,
                difficulty=diff,
                has_diagram=bool(row.get("has_diagram")),
                source_file=str(row.get("source_file") or "CBSE Sample Papers"),
                academic_year=str(row.get("session") or "2024-2025")
            )
            db.add(q_entry)
            cbse_inserted += 1

        db.commit()
        print(f"  Inserted {cbse_inserted} CBSE questions with resolved chapter names!")

        # 6. SEED VAISHNAVI'S 359 ICSE CLASS 10 QUESTIONS
        print("\n[6/8] Ingesting 359 ICSE Class 10 Questions with Diagrams (Vaishnavi)...")
        vaishnavi_sources = [
            ("Mathematics", "ICSE10_MATH", BASE_DIR / "vaishnavi" / "ICSC_MATHS_10_QuestionBank_FIXED" / "ICSC_MATHS_10_QuestionBank_with_hyperlinks" / "project" / "mathematics_questions.csv", "vaishnavi/ICSC_MATHS_10_QuestionBank_FIXED/ICSC_MATHS_10_QuestionBank_with_hyperlinks/project/"),
            ("Geography", "ICSE10_GEO", BASE_DIR / "vaishnavi" / "ICSE_GEOGRAPHY_10_QuestionBank (1)" / "geo" / "geography_questions.csv", "vaishnavi/ICSE_GEOGRAPHY_10_QuestionBank (1)/geo/"),
            ("History & Civics", "ICSE10_HCG", BASE_DIR / "vaishnavi" / "ICSE_HISTORY_CIVICS_10_QuestionBank" / "ICSE_HISTORY_CIVICS_10_QuestionBank" / "project" / "history_civics_questions.csv", "vaishnavi/ICSE_HISTORY_CIVICS_10_QuestionBank/ICSE_HISTORY_CIVICS_10_QuestionBank/project/")
        ]

        icse_inserted = 0
        for sname, scode, csv_file, rel_asset_base in vaishnavi_sources:
            if not csv_file.exists(): continue
            df_icse = pd.read_csv(csv_file)
            subj_obj = get_or_create_subject("ICSE", "10", sname, scode)
            
            for _, row in df_icse.iterrows():
                qid_raw = row.get("question_id")
                paper_no = row.get("paper_no", 1)
                canon_id = f"ICSE10_{scode}_{paper_no}_{qid_raw}_{row.get('sub_part', '')}".rstrip("_")
                
                ch_name = str(row.get("chapter") or "General Chapter").title()
                ch_obj = get_or_create_chapter(subj_obj, None, ch_name)
                
                has_diag = bool(str(row.get("has_diagram")).lower() == "yes" or row.get("has_diagram") == 1 or pd.notna(row.get("diagram_image")))
                diag_path = None
                if has_diag and pd.notna(row.get("diagram_image")):
                    diag_path = f"{rel_asset_base}{row.get('diagram_image')}"

                marks = float(row.get("marks", 1.0)) if pd.notna(row.get("marks")) else 1.0
                diff = str(row.get("difficulty") or "Medium").title()
                
                q_text = str(row.get("question_text", ""))
                q_type = "mcq_single" if "choose the correct" in q_text.lower() or "select" in q_text.lower() else ("short_answer" if marks <= 2 else "long_answer")

                q_entry = Question(
                    canonical_id=canon_id,
                    board_id=boards["ICSE"].id,
                    class_id=classes["10"].id,
                    subject_id=subj_obj.id,
                    chapter_id=ch_obj.id,
                    subject_name=subj_obj.name,
                    chapter_name=ch_obj.name,
                    topic_name=ch_obj.name,
                    question_number=int(row.get("question_number")) if pd.notna(row.get("question_number")) and str(row.get("question_number")).isdigit() else None,
                    sub_part=str(row.get("sub_part")) if pd.notna(row.get("sub_part")) else None,
                    question_type=q_type,
                    question_text=q_text,
                    marks=marks,
                    difficulty=diff,
                    has_diagram=has_diag,
                    diagram_url=diag_path,
                    source_file=f"ICSE Specimen & Solved Papers (Paper {paper_no})",
                    academic_year="2024-2026"
                )
                db.add(q_entry)
                icse_inserted += 1

        db.commit()
        print(f"  Inserted {icse_inserted} ICSE questions with diagrams!")

        # 7. SEED JEE SAMPLE QUESTIONS
        print("\n[7/8] Ingesting Clean JEE Sample Questions...")
        jee_clean_path = BASE_DIR / "JEE-assessment-RAG" / "questions_clean.json"
        jee_inserted = 0
        if jee_clean_path.exists():
            with open(jee_clean_path, "r", encoding="utf-8") as fp:
                jee_questions = json.load(fp)
            
            for jq in jee_questions:
                qnum = jq.get("question_number")
                canon_id = f"JEE_CLEAN_{qnum}"
                
                sname = jq.get("subject", "Mathematics")
                scode = f"JEE_{sname[:4].upper()}"
                subj_obj = get_or_create_subject("JEE", "JEE", sname, scode)
                ch_obj = get_or_create_chapter(subj_obj, None, "General JEE Syllabus")
                
                q_entry = Question(
                    canonical_id=canon_id,
                    board_id=boards["JEE"].id,
                    class_id=classes["JEE"].id,
                    subject_id=subj_obj.id,
                    chapter_id=ch_obj.id,
                    subject_name=sname,
                    chapter_name="General JEE Syllabus",
                    topic_name="General JEE Syllabus",
                    question_number=qnum,
                    question_type=jq.get("question_type", "mcq_single"),
                    question_text=jq.get("question_text", ""),
                    options=jq.get("options"),
                    correct_answer=jq.get("answer"),
                    solution=jq.get("solution"),
                    marks=4.0,
                    difficulty="Medium",
                    source_file="JEE Main Official Sample Paper"
                )
                db.add(q_entry)
                jee_inserted += 1

        db.commit()
        print(f"  Inserted {jee_inserted} JEE questions!")

        # 8. BLUEPRINTS & DEMO STUDENT
        print("\n[8/8] Finalizing Examination Blueprints & Demo Student...")
        s_cbse_math = get_or_create_subject("CBSE", "10", "Mathematics", "CBSE10_MATH")
        if not db.query(ExaminationBlueprint).filter(ExaminationBlueprint.title == "CBSE Class 10 Standard Mathematics Blueprint").first():
            bp1 = ExaminationBlueprint(
                board_id=boards["CBSE"].id,
                class_id=classes["10"].id,
                subject_id=s_cbse_math.id,
                title="CBSE Class 10 Standard Mathematics Blueprint",
                total_marks=80.0,
                duration_minutes=180,
                structure_config={
                    "sections": [
                        {"section_name": "Section A", "description": "Multiple Choice Questions", "question_count": 20, "marks_per_question": 1.0, "question_type": "mcq_single"},
                        {"section_name": "Section B", "description": "Very Short Answer Questions", "question_count": 5, "marks_per_question": 2.0, "question_type": "short_answer"},
                        {"section_name": "Section C", "description": "Short Answer Questions", "question_count": 6, "marks_per_question": 3.0, "question_type": "short_answer"},
                        {"section_name": "Section D", "description": "Long Answer Questions", "question_count": 4, "marks_per_question": 5.0, "question_type": "long_answer"},
                        {"section_name": "Section E", "description": "Case Study Based Questions", "question_count": 3, "marks_per_question": 4.0, "question_type": "case_based"}
                    ]
                }
            )
            db.add(bp1)

        # Call weightages & extra blueprints populate script
        try:
            from portal.scripts import populate_weightages
        except Exception as e:
            print(f"Weightage population note: {e}")

        db.commit()
        print("\n" + "=" * 60)
        print("MASTER SEEDING COMPLETED SUCCESSFULLY!")
        print(f"Total Questions Ingested: {db.query(Question).count()}")
        print(f"Total Unique Chapters: {db.query(Chapter).count()}")
        print("=" * 60)

    finally:
        db.close()

if __name__ == "__main__":
    run_seed()
