from sqlalchemy.orm import Session
from difflib import SequenceMatcher
from typing import Optional, Tuple
from app.models.taxonomy import Chapter, Topic, Subtopic

class TaxonomyMatcher:
    def __init__(self, db: Session):
        self.db = db

    def match_topic_and_subtopic(
        self, 
        chapter_name: str, 
        topic_name: str, 
        subtopic_name: Optional[str] = None
    ) -> Tuple[Optional[int], Optional[int]]:
        """
        Returns (topic_id, subtopic_id) based on fuzzy similarity matching.
        """
        all_topics = self.db.query(Topic).all()
        best_topic = None
        best_topic_score = 0.0

        for t in all_topics:
            # Check similarity with topic name and parent chapter name
            score = self._similarity(topic_name.lower(), t.name.lower())
            if t.chapter and chapter_name:
                chap_score = self._similarity(chapter_name.lower(), t.chapter.name.lower())
                score = (score * 0.7) + (chap_score * 0.3)

            if score > best_topic_score:
                best_topic_score = score
                best_topic = t

        # Threshold for acceptable match
        matched_topic_id = best_topic.id if best_topic and best_topic_score >= 0.45 else None

        matched_subtopic_id = None
        if matched_topic_id and subtopic_name:
            subtopics = self.db.query(Subtopic).filter(Subtopic.topic_id == matched_topic_id).all()
            best_sub = None
            best_sub_score = 0.0
            for s in subtopics:
                sub_score = self._similarity(subtopic_name.lower(), s.name.lower())
                if sub_score > best_sub_score:
                    best_sub_score = sub_score
                    best_sub = s
            if best_sub and best_sub_score >= 0.45:
                matched_subtopic_id = best_sub.id

        # Fallback: if no match found, pick the first existing topic in DB
        if not matched_topic_id:
            fallback = self.db.query(Topic).first()
            if fallback:
                matched_topic_id = fallback.id

        return matched_topic_id, matched_subtopic_id

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        return SequenceMatcher(None, a, b).ratio()