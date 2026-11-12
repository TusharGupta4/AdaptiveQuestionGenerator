from collections import defaultdict
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.submission import Student, StudentAnswer, SubmissionStatus
from app.models.profile import StudentTopicMastery, MasteryStatus
from app.models.taxonomy import Topic, Subtopic
from app.schemas.profile import (
    StudentKnowledgeProfileResponse, 
    TopicMasteryDetail, 
    SubtopicMasteryDetail
)

class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def generate_student_profile(self, student_id: int) -> StudentKnowledgeProfileResponse:
        student = self.db.query(Student).filter(Student.id == student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail=f"Student #{student_id} not found.")

        # 1. Fetch all evaluated answers for this student
        evaluated_answers = (
            self.db.query(StudentAnswer)
            .join(StudentAnswer.submission)
            .filter(
                StudentAnswer.submission.has(student_id=student_id),
                StudentAnswer.submission.has(status=SubmissionStatus.EVALUATED),
                StudentAnswer.marks_awarded.isnot(None)
            )
            .all()
        )

        if not evaluated_answers:
            raise HTTPException(status_code=400, detail="No evaluated tests found for this student yet.")

        # 2. Topic-wise and Subtopic-wise aggregation
        topic_stats = defaultdict(lambda: {"obtained": 0.0, "possible": 0.0, "attempts": 0})
        subtopic_stats = defaultdict(lambda: {"obtained": 0.0, "possible": 0.0, "attempts": 0})

        total_obtained = 0.0
        total_possible = 0.0

        for sa in evaluated_answers:
            q = sa.question
            awarded = sa.marks_awarded or 0.0
            possible = q.marks

            total_obtained += awarded
            total_possible += possible

            # Aggregate by Topic
            if q.topic_id:
                topic_stats[q.topic_id]["obtained"] += awarded
                topic_stats[q.topic_id]["possible"] += possible
                topic_stats[q.topic_id]["attempts"] += 1

            # Aggregate by Subtopic
            if q.subtopic_id:
                subtopic_stats[q.subtopic_id]["obtained"] += awarded
                subtopic_stats[q.subtopic_id]["possible"] += possible
                subtopic_stats[q.subtopic_id]["attempts"] += 1

        # 3. Classify Mastery & Update DB Cache
        strong_topics: list[str] = []
        moderate_topics: list[str] = []
        weak_topics: list[str] = []
        weak_subtopics: list[str] = []
        topic_details: list[TopicMasteryDetail] = []

        for t_id, data in topic_stats.items():
            topic = self.db.query(Topic).filter(Topic.id == t_id).first()
            if not topic:
                continue

            ratio = data["obtained"] / data["possible"] if data["possible"] > 0 else 0.0
            pct = round(ratio * 100, 1)

            if ratio >= 0.75:
                status = MasteryStatus.STRONG
                strong_topics.append(topic.name)
            elif ratio >= 0.40:
                status = MasteryStatus.MODERATE
                moderate_topics.append(topic.name)
            else:
                status = MasteryStatus.WEAK
                weak_topics.append(topic.name)

            topic_details.append(
                TopicMasteryDetail(
                    topic_id=t_id,
                    topic_name=topic.name,
                    chapter_name=topic.chapter.name if topic.chapter else "General",
                    marks_obtained=round(data["obtained"], 2),
                    marks_possible=round(data["possible"], 2),
                    accuracy_percentage=pct,
                    status=status
                )
            )

            # Upsert into student_topic_mastery DB table
            mastery_record = (
                self.db.query(StudentTopicMastery)
                .filter(StudentTopicMastery.student_id == student_id, StudentTopicMastery.topic_id == t_id)
                .first()
            )
            if not mastery_record:
                mastery_record = StudentTopicMastery(student_id=student_id, topic_id=t_id)
                self.db.add(mastery_record)

            mastery_record.attempts_count = data["attempts"]
            mastery_record.marks_obtained = data["obtained"]
            mastery_record.marks_possible = data["possible"]
            mastery_record.mastery_score = ratio
            mastery_record.status = status

        # 4. Process Subtopics
        for s_id, data in subtopic_stats.items():
            subtopic = self.db.query(Subtopic).filter(Subtopic.id == s_id).first()
            if not subtopic:
                continue
            ratio = data["obtained"] / data["possible"] if data["possible"] > 0 else 0.0
            if ratio < 0.50:
                weak_subtopics.append(subtopic.name)

        self.db.commit()

        # 5. Generate Pedagogical Diagnostic Recommendations
        recommendations = self._generate_recommendations(weak_topics, weak_subtopics, moderate_topics)

        overall_acc = round((total_obtained / total_possible * 100), 1) if total_possible > 0 else 0.0

        return StudentKnowledgeProfileResponse(
            student_id=student.id,
            student_name=student.name,
            roll_number=student.roll_number,
            overall_accuracy=overall_acc,
            total_questions_attempted=len(evaluated_answers),
            strong_topics=strong_topics,
            moderate_topics=moderate_topics,
            weak_topics=weak_topics,
            weak_subtopics=weak_subtopics,
            topic_performance=topic_details,
            recommendations=recommendations
        )

    @staticmethod
    def _generate_recommendations(weak_topics: list[str], weak_subtopics: list[str], moderate_topics: list[str]) -> list[str]:
        recs = []
        if weak_topics:
            recs.append(f"Critical focus needed in: {', '.join(weak_topics)}. Review fundamentals and solve foundational problems.")
        if weak_subtopics:
            recs.append(f"Specific subtopic weakness detected in '{', '.join(weak_subtopics)}'. Practice step-by-step formula applications.")
        if moderate_topics:
            recs.append(f"Good progress in {', '.join(moderate_topics)}. Solve timed practice questions to achieve mastery.")
        if not recs:
            recs.append("Excellent mastery across all tested topics! Ready for advanced and higher-difficulty papers.")
        return recs