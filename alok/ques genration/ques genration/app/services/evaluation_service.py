import json
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.submission import StudentSubmission, SubmissionStatus
from app.services.evaluator import AnswerEvaluator
from app.schemas.evaluation import SubmissionEvaluationReport, AnswerEvaluationResult

class EvaluationService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_submission(self, submission_id: int) -> SubmissionEvaluationReport:
        submission = self.db.query(StudentSubmission).filter(StudentSubmission.id == submission_id).first()
        if not submission:
            raise HTTPException(status_code=404, detail=f"Submission #{submission_id} not found.")

        total_awarded = 0.0
        total_possible = 0.0
        detailed_results: list[AnswerEvaluationResult] = []

        # Iterate through each segmented student answer
        for sa in submission.answers:
            question = sa.question
            total_possible += question.marks

            # Run evaluation
            eval_res = AnswerEvaluator.evaluate(
                question=question,
                question_number=sa.question_number,
                student_answer_text=sa.student_answer_text
            )

            # Persist in DB
            sa.marks_awarded = eval_res.marks_awarded
            sa.feedback = eval_res.feedback
            sa.step_scores = json.dumps([s.model_dump() for s in eval_res.step_evaluations])
            
            total_awarded += eval_res.marks_awarded
            detailed_results.append(eval_res)

        # Update Submission overall state
        submission.total_score = round(total_awarded, 2)
        submission.status = SubmissionStatus.EVALUATED
        self.db.commit()

        percentage = round((total_awarded / total_possible * 100), 2) if total_possible > 0 else 0.0

        return SubmissionEvaluationReport(
            submission_id=submission.id,
            student_name=submission.student.name,
            roll_number=submission.student.roll_number,
            paper_title=submission.paper.title,
            total_paper_marks=round(total_possible, 2),
            total_score_obtained=round(total_awarded, 2),
            percentage=percentage,
            status=submission.status.value,
            detailed_answers=detailed_results
        )