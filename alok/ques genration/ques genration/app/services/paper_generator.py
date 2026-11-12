import random
from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.taxonomy import Subject, Chapter, Topic
from app.models.question import Question, QuestionType
from app.models.paper import GeneratedPaper, PaperQuestion
from app.schemas.paper import CustomPaperRequest, SectionRule, GeneratedPaperResponse, PaperQuestionDetail

class PaperGeneratorEngine:
    def __init__(self, db: Session):
        self.db = db

    def generate_custom_paper(self, req: CustomPaperRequest) -> GeneratedPaperResponse:
        # 1. Validate Subject exists
        subject = self.db.query(Subject).filter(Subject.id == req.subject_id).first()
        if not subject:
            raise HTTPException(status_code=404, detail=f"Subject with ID {req.subject_id} not found.")

        # 2. Track selected question IDs to avoid duplicates
        used_question_ids: Set[int] = set()
        chosen_questions_by_section: Dict[str, List[Question]] = {}

        # 3. Process each section according to constraints
        for section in req.sections:
            selected = self._select_questions_for_section(
                section=section,
                subject_id=req.subject_id,
                chapter_ids=req.chapter_ids,
                excluded_ids=used_question_ids
            )
            chosen_questions_by_section[section.section_name] = selected
            for q in selected:
                used_question_ids.add(q.id)

        # 4. Save Generated Paper in Database
        db_paper = GeneratedPaper(
            title=req.title,
            subject_id=req.subject_id,
            total_marks=req.total_marks,
            duration_minutes=req.duration_minutes,
            blueprint=req.model_dump()
        )
        self.db.add(db_paper)
        self.db.flush()

        # 5. Save Question mappings with sequence numbers
        overall_q_num = 1
        response_sections: Dict[str, List[PaperQuestionDetail]] = {}

        for section_name, questions in chosen_questions_by_section.items():
            response_sections[section_name] = []
            for q in questions:
                pq = PaperQuestion(
                    paper_id=db_paper.id,
                    question_id=q.id,
                    section_name=section_name,
                    question_number=overall_q_num
                )
                self.db.add(pq)

                # Format options if MCQ
                opts = None
                if q.question_type == QuestionType.MCQ and q.options:
                    opts = [{"label": o.option_label, "text": o.option_text} for o in q.options]

                response_sections[section_name].append(
                    PaperQuestionDetail(
                        question_number=overall_q_num,
                        section_name=section_name,
                        question_id=q.id,
                        question_text=q.question_text,
                        question_type=q.question_type.value,
                        marks=q.marks,
                        difficulty=q.difficulty.value,
                        options=opts
                    )
                )
                overall_q_num += 1

        self.db.commit()

        return GeneratedPaperResponse(
            paper_id=db_paper.id,
            title=db_paper.title,
            subject_name=subject.name,
            total_marks=db_paper.total_marks,
            duration_minutes=db_paper.duration_minutes,
            sections=response_sections,
            total_questions=len(used_question_ids)
        )

    def _select_questions_for_section(
        self,
        section: SectionRule,
        subject_id: int,
        chapter_ids: Optional[List[int]],
        excluded_ids: Set[int]
    ) -> List[Question]:
        query = (
            self.db.query(Question)
            .join(Topic, Question.topic_id == Topic.id)
            .join(Chapter, Topic.chapter_id == Chapter.id)
        )

        # Filter by Subject
        query = query.filter(Chapter.subject_id == subject_id)

        # Filter by Question Type & Marks
        query = query.filter(Question.question_type == section.question_type)
        query = query.filter(Question.marks == section.marks_per_question)

        # Filter by Chapters if specified
        if chapter_ids:
            query = query.filter(Topic.chapter_id.in_(chapter_ids))

        # Filter by Difficulty if restricted
        if section.allowed_difficulty:
            query = query.filter(Question.difficulty.in_(section.allowed_difficulty))

        # Exclude already picked questions
        if excluded_ids:
            query = query.filter(~Question.id.in_(excluded_ids))

        available = query.all()

        if len(available) < section.question_count:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Insufficient questions in Question Bank for '{section.section_name}'. "
                    f"Required: {section.question_count} of type {section.question_type.value} "
                    f"({section.marks_per_question} marks), but only found {len(available)} available."
                )
            )

        # Randomize selection
        return random.sample(available, section.question_count)

    def generate_standard_paper(self, subject_id: int, pattern_name: str) -> GeneratedPaperResponse:
        """Standard Predefined Blueprints"""
        if pattern_name == "QUICK_TEST_10":
            req = CustomPaperRequest(
                title="Class 10 Mathematics - Standard Unit Test",
                subject_id=subject_id,
                total_marks=8.0,
                duration_minutes=30,
                sections=[
                    SectionRule(
                        section_name="Section A (Objective)",
                        question_type=QuestionType.MCQ,
                        marks_per_question=1.0,
                        question_count=2
                    ),
                    SectionRule(
                        section_name="Section B (Short Answer)",
                        question_type=QuestionType.SHORT,
                        marks_per_question=2.0,
                        question_count=3
                    )
                ]
            )
            return self.generate_custom_paper(req)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown pattern template '{pattern_name}'")