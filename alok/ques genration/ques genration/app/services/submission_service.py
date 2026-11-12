from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.paper import GeneratedPaper, PaperQuestion
from app.models.submission import Student, StudentSubmission, StudentAnswer, SubmissionStatus
from app.services.ocr_service import OCRService
from app.services.answer_segmenter import AnswerSegmenter
from app.schemas.submission import SubmissionResponse, StudentAnswerDetail

class SubmissionService:
    def __init__(self, db: Session):
        self.db = db

    def process_submission(
        self,
        paper_id: int,
        student_roll: str,
        student_name: str,
        file_path: str
    ) -> SubmissionResponse:
        # 1. Verify Paper exists
        paper = self.db.query(GeneratedPaper).filter(GeneratedPaper.id == paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail=f"Paper #{paper_id} not found.")

        # 2. Find or Create Student
        student = self.db.query(Student).filter(Student.roll_number == student_roll).first()
        if not student:
            student = Student(name=student_name, roll_number=student_roll)
            self.db.add(student)
            self.db.flush()

        # 3. Perform OCR
        raw_text = OCRService.extract_text(file_path)

        # 4. Segment Answers
        segmented_dict = AnswerSegmenter.segment_answers(raw_text)

        # 5. Create Submission Record
        submission = StudentSubmission(
            student_id=student.id,
            paper_id=paper.id,
            file_path=file_path,
            raw_ocr_text=raw_text,
            status=SubmissionStatus.PENDING_EVALUATION
        )
        self.db.add(submission)
        self.db.flush()

        # 6. Map Answers to the Paper's Actual Questions
        answers_detail: list[StudentAnswerDetail] = []
        for pq in paper.paper_questions:
            student_answer_text = segmented_dict.get(
                pq.question_number, 
                "Not attempted / Blank answer sheet section."
            )

            student_ans = StudentAnswer(
                submission_id=submission.id,
                question_id=pq.question_id,
                question_number=pq.question_number,
                student_answer_text=student_answer_text
            )
            self.db.add(student_ans)

            answers_detail.append(
                StudentAnswerDetail(
                    question_number=pq.question_number,
                    question_id=pq.question.id,
                    question_text=pq.question.question_text,
                    student_answer_text=student_answer_text,
                    marks_allocated=pq.question.marks
                )
            )

        self.db.commit()

        return SubmissionResponse(
            submission_id=submission.id,
            student_name=student.name,
            roll_number=student.roll_number,
            paper_id=paper.id,
            paper_title=paper.title,
            total_answers_extracted=len(segmented_dict),
            status=submission.status.value,
            answers=answers_detail,
            submitted_at=submission.submitted_at
        )