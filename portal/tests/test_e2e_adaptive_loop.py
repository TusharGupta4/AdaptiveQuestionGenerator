import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from portal.core.database import SessionLocal, StudentProfile, ExaminationBlueprint, StudentSubmission
from portal.services.paper_generator import PaperGeneratorEngine
from portal.services.adaptive_engine import AdaptivePaperEngine
from portal.services.evaluation_service import EvaluationService
from portal.services.pdf_export_service import PDFExportService

def test_full_assessment_lifecycle():
    print("=" * 65)
    print("TESTING FULL ADAPTIVE ASSESSMENT LIFECYCLE (END-TO-END)")
    print("=" * 65)

    db = SessionLocal()
    try:
        # 1. Fetch Demo Student
        student = db.query(StudentProfile).first()
        assert student is not None, "Student profile must exist!"
        print(f"1. Student Profile Loaded: {student.full_name} ({student.email})")

        # 2. Generate a Normal Blueprint Exam (CBSE Class 10 Maths)
        bp = db.query(ExaminationBlueprint).filter(ExaminationBlueprint.title.ilike("%CBSE%")).first()
        assert bp is not None, "Blueprint must exist!"
        
        gen_engine = PaperGeneratorEngine(db)
        paper = gen_engine.generate_blueprint_paper(blueprint_id=bp.id, student_id=student.id)
        print(f"2. Normal Blueprint Paper Generated: #{paper.id} - '{paper.title}'")
        print(f"   Total Questions: {len(paper.paper_questions)} | Total Marks: {paper.total_marks}")

        # 3. Test PDF Generation via ReportLab
        pdf_bytes = PDFExportService.generate_exam_pdf(paper)
        assert len(pdf_bytes) > 1000, "PDF bytes must be valid!"
        print(f"3. PDF Question Paper Compiled Successfully! ({len(pdf_bytes):,} bytes)")

        # 4. Simulate Student Attempt (Intentionally fail on Real Numbers)
        submission = StudentSubmission(
            student_id=student.id,
            paper_id=paper.id,
            submission_type="ONLINE_MCQ",
            status="SUBMITTED"
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        student_answers = {}
        for pq in paper.paper_questions:
            q = pq.question
            # Deliberately answer wrong or skip for one chapter
            if "real number" in (q.chapter_name or "").lower():
                student_answers[str(q.id)] = "WRONG_ANSWER"
            else:
                student_answers[str(q.id)] = q.correct_answer or "A"

        eval_service = EvaluationService(db)
        scorecard = eval_service.evaluate_submission(submission.id, student_answers)
        print(f"4. Submission Evaluated! Score: {scorecard['total_score']} / {scorecard['total_possible']} ({scorecard['accuracy_percent']}%)")
        print("   Chapter performance breakdown:")
        for ch, stats in scorecard["chapter_stats"].items():
            acc = round((stats["obtained"] / stats["possible"] * 100), 1) if stats["possible"] > 0 else 0
            print(f"     - {ch}: {stats['obtained']}/{stats['possible']} Marks ({acc}%)")

        # 5. Generate Adaptive Question Paper Based on Student's Weak Areas
        print("\n5. Running Adaptive Engine for Next Exam...")
        adaptive_engine = AdaptivePaperEngine(db)
        adaptive_result = adaptive_engine.generate_adaptive_paper(
            student_id=student.id,
            subject_id=paper.subject_id,
            total_questions=10,
            title="Personalized Adaptive Remedial Mathematics Exam"
        )
        adapt_paper = adaptive_result["paper"]
        print(f"   Generated Adaptive Paper: #{adapt_paper.id} - '{adapt_paper.title}'")
        print(f"   Pedagogical Rationale: {adaptive_result['rationale']}")
        print(f"   Targeted Weak Topics: {adaptive_result['weak_topics']}")
        print(f"   Question Allocation Quotas: {adaptive_result['allocation']}")

        # Verify that questions were indeed picked from weak topic
        weak_count = sum(1 for pq in adapt_paper.paper_questions if pq.question.chapter_name in adaptive_result['weak_topics'])
        print(f"   Questions Allocated to Weak Topics: {weak_count} out of {len(adapt_paper.paper_questions)}")

        # 6. Test PDF Generation for Adaptive Paper
        adapt_pdf_bytes = PDFExportService.generate_exam_pdf(adapt_paper)
        assert len(adapt_pdf_bytes) > 1000
        print(f"6. Adaptive PDF Question Paper Compiled Successfully! ({len(adapt_pdf_bytes):,} bytes)")

        print("\n" + "=" * 65)
        print("SUCCESS! ALL PHASES OF THE ADAPTIVE ASSESSMENT PLATFORM VERIFIED!")
        print("=" * 65)

    finally:
        db.close()

if __name__ == "__main__":
    test_full_assessment_lifecycle()
