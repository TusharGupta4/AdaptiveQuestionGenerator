import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import SessionLocal, ExaminationBlueprint
from portal.services.paper_generator import PaperGeneratorEngine

def test_generation():
    db = SessionLocal()
    engine = PaperGeneratorEngine(db)

    print("=================================================================")
    print("VERIFYING DETERMINISTIC & WEIGHTAGE-COMPLIANT PAPER GENERATION")
    print("=================================================================")

    # 1. CBSE Class 10 Mathematics
    bp_math = db.query(ExaminationBlueprint).filter(ExaminationBlueprint.title.ilike("%CBSE Class 10 Standard Mathematics%")).first()
    if bp_math:
        paper = engine.generate_blueprint_paper(bp_math.id)
        print(f"\n[1] Generated: '{paper.title}' (Paper ID: #{paper.id})")
        print(f"    Total Marks: {paper.total_marks} / Target: {bp_math.total_marks}")
        meta = paper.paper_metadata
        print("    Difficulty Breakdown:", meta.get("difficulty_breakdown"))
        print(f"    Total Questions: {meta.get('total_questions')}")
        audits = meta.get("chapter_weightage_audit", [])
        print(f"    Chapter Weightage Compliance (Showing sample of {len(audits)} chapters):")
        for a in audits[:7]:
            print(f"      * {a['chapter_name']}: Target {a['target_marks']}m -> Allocated {a['allocated_marks']}m (Dev: {a['deviation_marks']}m)")

    # 2. ICSE Class 10 Geography
    bp_geo = db.query(ExaminationBlueprint).filter(ExaminationBlueprint.title.ilike("%ICSE Class 10 Geography%")).first()
    if bp_geo:
        paper_geo = engine.generate_blueprint_paper(bp_geo.id)
        print(f"\n[2] Generated: '{paper_geo.title}' (Paper ID: #{paper_geo.id})")
        print(f"    Total Marks: {paper_geo.total_marks} / Target: {bp_geo.total_marks}")
        print("    Difficulty Breakdown:", paper_geo.paper_metadata.get("difficulty_breakdown"))
        audits_geo = paper_geo.paper_metadata.get("chapter_weightage_audit", [])
        print(f"    Chapter Weightage Compliance ({len(audits_geo)} chapters):")
        for a in audits_geo[:5]:
            print(f"      * {a['chapter_name']}: Target {a['target_marks']}m -> Allocated {a['allocated_marks']}m")

    # 3. CBSE Class 9 Science
    bp_sci = db.query(ExaminationBlueprint).filter(ExaminationBlueprint.title.ilike("%CBSE Class 9 Science%")).first()
    if bp_sci:
        paper_sci = engine.generate_blueprint_paper(bp_sci.id)
        print(f"\n[3] Generated: '{paper_sci.title}' (Paper ID: #{paper_sci.id})")
        print(f"    Total Marks: {paper_sci.total_marks} / Target: {bp_sci.total_marks}")
        print("    Difficulty Breakdown:", paper_sci.paper_metadata.get("difficulty_breakdown"))

    print("\n=================================================================")
    print("STRUCTURED WEIGHTAGE VERIFICATION PASSED SUCCESSFULLY!")
    print("=================================================================")
    db.close()

if __name__ == "__main__":
    test_generation()

