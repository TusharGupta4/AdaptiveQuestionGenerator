import random
from typing import List, Dict, Any, Optional, Set
from sqlalchemy.orm import Session
from portal.core.database import (
    Question, GeneratedPaper, PaperQuestion, StudentProfile,
    StudentSubmission, StudentAnswer, StudentTopicMastery, Chapter, Subject
)

class AdaptivePaperEngine:
    def __init__(self, db: Session):
        self.db = db

    def generate_adaptive_paper(
        self,
        student_id: int,
        subject_id: int,
        total_questions: int = 15,
        title: Optional[str] = None
    ) -> Dict[str, Any]:
        student = self.db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
        if not student:
            raise ValueError(f"Student #{student_id} not found.")

        subject = self.db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            raise ValueError(f"Subject #{subject_id} not found.")

        # 1. Fetch previously attempted question IDs to avoid repetition
        attempted_qids: Set[int] = {
            ans.question_id for ans in
            self.db.query(StudentAnswer.question_id)
            .join(StudentSubmission, StudentAnswer.submission_id == StudentSubmission.id)
            .filter(StudentSubmission.student_id == student_id)
            .all()
        }

        # 2. Inspect Student Topic Mastery
        mastery_records = self.db.query(StudentTopicMastery).filter(
            StudentTopicMastery.student_id == student_id,
            StudentTopicMastery.subject_id == subject_id
        ).all()

        high_priority_chapters = []   # Needs Improvement (<50% accuracy)
        medium_priority_chapters = [] # Developing (50% - 79% accuracy)
        low_priority_chapters = []    # Mastered (>=80% accuracy)

        for m in mastery_records:
            ch_name = m.chapter_name or (m.chapter.name if m.chapter else None)
            if not ch_name: continue
            
            acc = float(m.accuracy_percentage or 0.0)
            if acc < 50.0 and m.total_attempts > 0:
                high_priority_chapters.append(ch_name)
            elif 50.0 <= acc < 80.0:
                medium_priority_chapters.append(ch_name)
            elif acc >= 80.0:
                low_priority_chapters.append(ch_name)

        is_cold_start = (len(high_priority_chapters) == 0 and len(medium_priority_chapters) == 0)

        # 3. Quota Partitioning with Hard Ceiling (max 30% per topic)
        max_per_topic = max(2, int(total_questions * 0.30))
        allocation = {}

        if is_cold_start:
            # Diagnostic Baseline mode across all available chapters
            rationale = "Diagnostic Baseline Mode: New student session. Questions distributed across the complete syllabus to establish a baseline."
            all_chapters = [c.name for c in self.db.query(Chapter).filter(Chapter.subject_id == subject_id).all()]
            if not all_chapters:
                all_chapters = [q[0] for q in self.db.query(Question.chapter_name).filter(Question.subject_id == subject_id).distinct().all() if q[0]]
            
            per_chap = max(1, total_questions // max(1, len(all_chapters)))
            for cname in all_chapters:
                allocation[cname] = min(per_chap, max_per_topic)
        else:
            rationale = f"Adaptive Remedial Mode: Focusing 60% on weak topics ({len(high_priority_chapters)} detected), 25% on average topics, and 15% on retention."
            high_quota = max(1, int(total_questions * 0.60))
            med_quota = max(1, int(total_questions * 0.25))
            ret_quota = total_questions - (high_quota + med_quota)

            # Distribute high quota
            if high_priority_chapters:
                per_high = max(1, high_quota // len(high_priority_chapters))
                for ch in high_priority_chapters:
                    allocation[ch] = min(per_high, max_per_topic)
            
            # Distribute med quota
            if medium_priority_chapters:
                per_med = max(1, med_quota // len(medium_priority_chapters))
                for ch in medium_priority_chapters:
                    allocation[ch] = allocation.get(ch, 0) + min(per_med, max_per_topic)

        # 4. Greedy Question Selection from Database
        selected_questions: List[Question] = []
        used_ids = set()

        def pick_from_chapter(chap_name: str, count: int, pref_difficulty: Optional[str] = None):
            q_query = self.db.query(Question).filter(
                Question.subject_id == subject_id,
                Question.chapter_name == chap_name,
                Question.is_active == True,
                ~Question.id.in_(attempted_qids),
                ~Question.id.in_(used_ids)
            )
            if pref_difficulty:
                q_diff = q_query.filter(Question.difficulty == pref_difficulty).all()
                if len(q_diff) >= count:
                    return random.sample(q_diff, count)
            
            candidates = q_query.all()
            if not candidates:
                # If all unseen questions exhausted, allow review from previously attempted
                candidates = self.db.query(Question).filter(
                    Question.subject_id == subject_id,
                    Question.chapter_name == chap_name,
                    Question.is_active == True,
                    ~Question.id.in_(used_ids)
                ).all()
            return random.sample(candidates, min(len(candidates), count)) if candidates else []

        for ch_name, req_count in allocation.items():
            # If high priority -> prefer Easy/Medium difficulty
            pref_diff = "Easy" if ch_name in high_priority_chapters else ("Hard" if ch_name in low_priority_chapters else "Medium")
            picked = pick_from_chapter(ch_name, req_count, pref_diff)
            for q in picked:
                used_ids.add(q.id)
                selected_questions.append(q)

        # If still short of total_questions, fill from general pool
        if len(selected_questions) < total_questions:
            filler = self.db.query(Question).filter(
                Question.subject_id == subject_id,
                Question.is_active == True,
                ~Question.id.in_(used_ids)
            ).all()
            needed = total_questions - len(selected_questions)
            if filler:
                for q in random.sample(filler, min(len(filler), needed)):
                    used_ids.add(q.id)
                    selected_questions.append(q)

        total_marks = sum(float(q.marks or 1.0) for q in selected_questions)

        # 5. Save Generated Paper
        paper_title = title or f"Adaptive Remedial Test - {subject.name}"
        db_paper = GeneratedPaper(
            title=paper_title,
            board_id=student.board_id,
            class_id=student.class_id,
            subject_id=subject_id,
            is_adaptive=True,
            total_marks=total_marks,
            duration_minutes=max(30, int(len(selected_questions) * 2.5)),
            created_by=student_id,
            paper_metadata={
                "adaptive_rationale": rationale,
                "high_priority_chapters": high_priority_chapters,
                "medium_priority_chapters": medium_priority_chapters,
                "allocation_breakdown": allocation
            }
        )
        self.db.add(db_paper)
        self.db.flush()

        for idx, q in enumerate(selected_questions, start=1):
            sec_name = "Remedial Section" if q.chapter_name in high_priority_chapters else "Curriculum Section"
            pq = PaperQuestion(
                paper_id=db_paper.id,
                question_id=q.id,
                section_name=sec_name,
                question_number=idx,
                allocated_marks=float(q.marks or 1.0)
            )
            self.db.add(pq)

        self.db.commit()
        self.db.refresh(db_paper)

        return {
            "paper": db_paper,
            "questions": selected_questions,
            "rationale": rationale,
            "allocation": allocation,
            "weak_topics": high_priority_chapters
        }
