import os
import re
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from portal.core.database import (
    StudentSubmission, StudentAnswer, Question, StudentTopicMastery,
    GeneratedPaper, Board
)

class EvaluationService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate_submission(
        self,
        submission_id: int,
        answers_dict: Dict[str, str]
    ) -> Dict[str, Any]:
        submission = self.db.query(StudentSubmission).filter(StudentSubmission.id == submission_id).first()
        if not submission:
            raise ValueError(f"Submission #{submission_id} not found.")

        paper = submission.paper
        is_jee = bool(paper.board and paper.board.code == "JEE")

        total_awarded = 0.0
        total_possible = 0.0
        correct_count = 0
        wrong_count = 0
        unattempted_count = 0

        # Chapter-level accumulator for mastery updates
        chapter_stats = {}

        # Fetch all questions in this paper
        paper_questions = paper.paper_questions

        for pq in paper_questions:
            q = pq.question
            qid_str = str(q.id)
            student_text = answers_dict.get(qid_str, "").strip()
            max_m = float(pq.allocated_marks or q.marks or 1.0)
            total_possible += max_m

            ch_name = q.chapter_name or "General"
            if ch_name not in chapter_stats:
                chapter_stats[ch_name] = {"obtained": 0.0, "possible": 0.0, "correct": 0, "wrong": 0, "unattempted": 0, "chapter_id": q.chapter_id, "subject_id": q.subject_id}
            chapter_stats[ch_name]["possible"] += max_m

            if not student_text or student_text.lower() in ["not attempted", "unattempted", "skip"]:
                unattempted_count += 1
                chapter_stats[ch_name]["unattempted"] += 1
                sa = StudentAnswer(
                    submission_id=submission.id,
                    question_id=q.id,
                    question_number=pq.question_number,
                    student_text="[Not Attempted]",
                    marks_awarded=0.0,
                    max_marks=max_m,
                    is_correct=False,
                    evaluator_feedback="Question not attempted."
                )
                self.db.add(sa)
                continue

            # 1. MCQ Evaluation
            if q.question_type == "mcq_single":
                is_correct = False
                corr = str(q.correct_answer or "").strip().upper()
                s_ans = student_text.strip().upper()

                # Match by letter A/B/C/D
                if s_ans.startswith(corr) or s_ans == corr:
                    is_correct = True
                elif q.options and isinstance(q.options, dict):
                    # Check text match
                    opt_val = q.options.get(corr, "")
                    if opt_val and (opt_val.lower() in student_text.lower() or student_text.lower() in opt_val.lower()):
                        is_correct = True

                if is_correct:
                    marks_awarded = max_m if not is_jee else 4.0
                    correct_count += 1
                    chapter_stats[ch_name]["correct"] += 1
                    feedback = "Correct option selected."
                else:
                    marks_awarded = 0.0 if not is_jee else -1.0
                    wrong_count += 1
                    chapter_stats[ch_name]["wrong"] += 1
                    feedback = f"Incorrect. Correct answer is option ({corr})."

            # 2. Numerical / Short / Long Answer Evaluation
            else:
                marks_awarded, is_correct, feedback = self._evaluate_descriptive(q, student_text, max_m)
                if is_correct:
                    correct_count += 1
                    chapter_stats[ch_name]["correct"] += 1
                else:
                    wrong_count += 1
                    chapter_stats[ch_name]["wrong"] += 1

            total_awarded += marks_awarded
            chapter_stats[ch_name]["obtained"] += marks_awarded

            sa = StudentAnswer(
                submission_id=submission.id,
                question_id=q.id,
                question_number=pq.question_number,
                student_text=student_text,
                marks_awarded=marks_awarded,
                max_marks=max_m,
                is_correct=is_correct,
                evaluator_feedback=feedback
            )
            self.db.add(sa)

        # 3. Update Submission Totals
        submission.total_score = max(0.0, total_awarded)
        submission.accuracy_percent = round((total_awarded / total_possible * 100), 2) if total_possible > 0 else 0.0
        submission.status = "EVALUATED"

        # 4. Update Student Topic Mastery Table
        for ch_name, stats in chapter_stats.items():
            mastery = self.db.query(StudentTopicMastery).filter(
                StudentTopicMastery.student_id == submission.student_id,
                StudentTopicMastery.chapter_name == ch_name
            ).first()

            if not mastery:
                mastery = StudentTopicMastery(
                    student_id=submission.student_id,
                    subject_id=stats["subject_id"],
                    chapter_id=stats["chapter_id"],
                    chapter_name=ch_name
                )
                self.db.add(mastery)

            mastery.total_attempts = (mastery.total_attempts or 0) + (stats["correct"] + stats["wrong"])
            mastery.total_correct = (mastery.total_correct or 0) + stats["correct"]
            mastery.total_wrong = (mastery.total_wrong or 0) + stats["wrong"]
            mastery.total_unattempted = (mastery.total_unattempted or 0) + stats["unattempted"]
            mastery.marks_obtained = float(mastery.marks_obtained or 0.0) + stats["obtained"]
            mastery.marks_possible = float(mastery.marks_possible or 0.0) + stats["possible"]

            if mastery.marks_possible > 0:
                acc = (mastery.marks_obtained / mastery.marks_possible) * 100
                mastery.accuracy_percentage = round(acc, 2)
                if acc >= 80.0:
                    mastery.mastery_status = "Strong"
                elif acc >= 50.0:
                    mastery.mastery_status = "Average"
                else:
                    mastery.mastery_status = "Needs Improvement"

        self.db.commit()
        self.db.refresh(submission)

        return {
            "submission_id": submission.id,
            "total_score": float(submission.total_score),
            "total_possible": total_possible,
            "accuracy_percent": float(submission.accuracy_percent),
            "correct_count": correct_count,
            "wrong_count": wrong_count,
            "unattempted_count": unattempted_count,
            "chapter_stats": chapter_stats
        }

    def _evaluate_descriptive(self, question: Question, student_text: str, max_marks: float):
        """Rubric-based evaluation supporting partial marking and LLM or keyword fallback."""
        corr = str(question.correct_answer or "").strip()
        
        # Check exact numerical match
        if question.question_type == "numerical":
            s_clean = re.sub(r"[^\d.-]", "", student_text)
            c_clean = re.sub(r"[^\d.-]", "", corr)
            if s_clean and c_clean:
                try:
                    if abs(float(s_clean) - float(c_clean)) < 0.01:
                        return max_marks, True, "Correct numerical value."
                except ValueError:
                    pass

        # Keywords / Concepts match
        key_terms = [w.lower() for w in re.split(r"\W+", corr) if len(w) > 3]
        if key_terms:
            matches = sum(1 for term in key_terms if term in student_text.lower())
            ratio = matches / len(key_terms)
            awarded = round(ratio * max_marks, 1)
            is_correct = ratio >= 0.70
            feedback = f"Key concepts coverage: {int(ratio*100)}%. Awarded partial marks: {awarded}/{max_marks}."
            return awarded, is_correct, feedback

        # Default heuristic based on effort / length
        word_count = len(student_text.split())
        if word_count >= 15:
            awarded = round(max_marks * 0.75, 1)
            return awarded, True, f"Answer submitted with sufficient explanation ({word_count} words)."
        elif word_count >= 5:
            awarded = round(max_marks * 0.50, 1)
            return awarded, False, f"Partially complete response ({word_count} words)."
        else:
            return 0.0, False, "Response too brief or insufficient."
