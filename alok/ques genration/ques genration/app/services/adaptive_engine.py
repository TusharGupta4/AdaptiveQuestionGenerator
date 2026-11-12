import random
from typing import List, Set, Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.submission import Student, StudentAnswer
from app.models.taxonomy import Topic
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.paper import GeneratedPaper, PaperQuestion
from app.schemas.adaptive import (
    AdaptivePaperRequest, 
    AdaptivePaperResponse, 
    AdaptiveTopicAllocation
)
from app.schemas.paper import GeneratedPaperResponse, PaperQuestionDetail
from app.services.analytics_service import AnalyticsService
from app.services.paper_renderer import PaperRenderer

class AdaptivePaperEngine:
    def __init__(self, db: Session):
        self.db = db
        self.analytics = AnalyticsService(db)

    def generate_adaptive_paper(self, req: AdaptivePaperRequest) -> AdaptivePaperResponse:
        # 1. Fetch Student and Knowledge Profile
        student = self.db.query(Student).filter(Student.id == req.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail=f"Student #{req.student_id} not found.")

        profile = self.analytics.generate_student_profile(req.student_id)

        # 2. Get questions previously attempted by the student (to avoid repetition)
        previously_attempted_qids: Set[int] = {
            ans.question_id for ans in 
            self.db.query(StudentAnswer)
            .join(StudentAnswer.submission)
            .filter(StudentAnswer.submission.has(student_id=req.student_id))
            .all()
        }

        # 3. Categorize Topics by Mastery
        weak_topic_objs = self.db.query(Topic).filter(Topic.name.in_(profile.weak_topics)).all()
        mod_topic_objs = self.db.query(Topic).filter(Topic.name.in_(profile.moderate_topics)).all()
        strong_topic_objs = self.db.query(Topic).filter(Topic.name.in_(profile.strong_topics)).all()

        # If student has no weak topics (e.g. scored 100%), take moderate/all topics
        target_primary_topics = weak_topic_objs if weak_topic_objs else (mod_topic_objs or strong_topic_objs)
        target_primary_ids = [t.id for t in target_primary_topics]

        # 4. Greedy Constraint Solver for Adaptive Selection
        # Target: Fill ~60-70% from Weak/Primary topics, rest from others
        selected_questions: List[Question] = []
        current_marks = 0.0

        # Query eligible pool from DB
        def get_candidates(topic_ids: List[int], exclude: Set[int]):
            q = self.db.query(Question)
            if topic_ids:
                q = q.filter(Question.topic_id.in_(topic_ids))
            if exclude:
                q = q.filter(~Question.id.in_(exclude))
            return q.all()

        used_ids = set()

        # Pass 1: Prioritize Weak Topics (prefer questions not seen before)
        primary_candidates = get_candidates(target_primary_ids, previously_attempted_qids)
        # If not enough unseen questions, allow review of previous questions
        if not primary_candidates:
            primary_candidates = get_candidates(target_primary_ids, set())

        random.shuffle(primary_candidates)

        for q in primary_candidates:
            if current_marks + q.marks <= req.total_marks:
                selected_questions.append(q)
                current_marks += q.marks
                used_ids.add(q.id)
                if current_marks >= req.total_marks:
                    break

        # Pass 2: If marks still needed, fill from other topics
        if current_marks < req.total_marks:
            other_candidates = get_candidates([], previously_attempted_qids.union(used_ids))
            if not other_candidates:
                other_candidates = get_candidates([], used_ids)
            random.shuffle(other_candidates)

            for q in other_candidates:
                if current_marks + q.marks <= req.total_marks:
                    selected_questions.append(q)
                    current_marks += q.marks
                    used_ids.add(q.id)
                    if current_marks >= req.total_marks:
                        break

        if not selected_questions:
            raise HTTPException(status_code=400, detail="Unable to assemble questions satisfying adaptive constraints.")

        # 5. Persist Generated Adaptive Paper in DB
        subject_id = selected_questions[0].topic.chapter.subject_id if selected_questions[0].topic else 1
        db_paper = GeneratedPaper(
            title=f"{req.title} for {student.name}",
            subject_id=subject_id,
            total_marks=current_marks,
            duration_minutes=req.duration_minutes,
            blueprint={
                "type": "ADAPTIVE",
                "focus_mode": req.focus_mode,
                "student_id": req.student_id,
                "targeted_weak_topics": profile.weak_topics
            }
        )
        self.db.add(db_paper)
        self.db.flush()

        # 6. Map Paper Questions & Build Response
        response_sections: Dict[str, List[PaperQuestionDetail]] = {"Adaptive Diagnostic Section": []}
        topic_count_map = {}

        for idx, q in enumerate(selected_questions, start=1):
            pq = PaperQuestion(
                paper_id=db_paper.id,
                question_id=q.id,
                section_name="Adaptive Diagnostic Section",
                question_number=idx
            )
            self.db.add(pq)

            opts = None
            if q.question_type == QuestionType.MCQ and q.options:
                opts = [{"label": o.option_label, "text": o.option_text} for o in q.options]

            response_sections["Adaptive Diagnostic Section"].append(
                PaperQuestionDetail(
                    question_number=idx,
                    section_name="Adaptive Diagnostic Section",
                    question_id=q.id,
                    question_text=q.question_text,
                    question_type=q.question_type.value,
                    marks=q.marks,
                    difficulty=q.difficulty.value,
                    options=opts
                )
            )

            # Track topic stats for summary
            t_name = q.topic.name if q.topic else "General"
            if t_name not in topic_count_map:
                topic_count_map[t_name] = {"marks": 0.0, "count": 0}
            topic_count_map[t_name]["marks"] += q.marks
            topic_count_map[t_name]["count"] += 1

        self.db.commit()

        # Build Topic Allocations
        topic_allocations = []
        for t_name, data in topic_count_map.items():
            st = "WEAK (Targeted)" if t_name in profile.weak_topics else ("MODERATE" if t_name in profile.moderate_topics else "STRONG")
            topic_allocations.append(
                AdaptiveTopicAllocation(
                    topic_name=t_name,
                    status=st,
                    allocated_marks=data["marks"],
                    questions_count=data["count"]
                )
            )

        paper_resp = GeneratedPaperResponse(
            paper_id=db_paper.id,
            title=db_paper.title,
            subject_name="Mathematics",
            total_marks=db_paper.total_marks,
            duration_minutes=db_paper.duration_minutes,
            sections=response_sections,
            total_questions=len(selected_questions)
        )

        # Render printable HTML file
        PaperRenderer.render_to_html(paper_resp)

        rationale = (
            f"Paper tailored for {student.name}. "
            f"Prioritized weak topics ({', '.join(profile.weak_topics) if profile.weak_topics else 'all topics'}) "
            f"to bridge diagnosed conceptual gaps while adjusting difficulty."
        )

        return AdaptivePaperResponse(
            paper_details=paper_resp,
            student_id=student.id,
            student_name=student.name,
            remedial_focus_topics=profile.weak_topics,
            topic_allocation_summary=topic_allocations,
            pedagogical_rationale=rationale
        )