from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, BigInteger, String, Text, 
    Numeric, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from portal.core.config import DATABASE_URL, DEFAULT_SQLITE_URL

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    # Test connection
    with engine.connect() as conn:
        pass
except Exception as e:
    print(f"[Warning] Failed connecting to primary DATABASE_URL ({e}). Falling back to SQLite.")
    engine = create_engine(DEFAULT_SQLITE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ============================================================================
# 1. TAXONOMY & CURRICULUM
# ============================================================================

class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False)   # 'CBSE', 'ICSE', 'ISC', 'JEE'
    name = Column(String(100), nullable=False)

    subjects = relationship("Subject", back_populates="board", cascade="all, delete-orphan")


class AcademicClass(Base):
    __tablename__ = "academic_classes"

    id = Column(Integer, primary_key=True, index=True)
    grade = Column(String(20), nullable=False)               # 'Class 9', 'Class 10', 'Class 11', 'Class 12', 'Competitive'
    code = Column(String(20), unique=True, nullable=False)   # '9', '10', '11', '12', 'JEE'

    subjects = relationship("Subject", back_populates="academic_class", cascade="all, delete-orphan")


class AcademicStream(Base):
    __tablename__ = "academic_streams"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)                # 'General', 'Science', 'Commerce', 'Humanities'


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(Integer, ForeignKey("academic_classes.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)               # 'Mathematics', 'Physics', 'History & Civics'
    code = Column(String(50), nullable=False)                # 'CBSE10_MATH', 'ICSE10_GEO', 'JEE_CHEM'

    board = relationship("Board", back_populates="subjects")
    academic_class = relationship("AcademicClass", back_populates="subjects")
    chapters = relationship("Chapter", back_populates="subject", cascade="all, delete-orphan")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    chapter_code = Column(String(50), index=True)            # 'CBSE10_MATH_01', 'JEE_MATH_CALCULUS'
    name = Column(Text, nullable=False)
    chapter_number = Column(Integer, nullable=True)

    subject = relationship("Subject", back_populates="chapters")
    topics = relationship("Topic", back_populates="chapter", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False)
    topic_code = Column(String(50), index=True)
    name = Column(Text, nullable=False)

    chapter = relationship("Chapter", back_populates="topics")
    questions = relationship("Question", back_populates="topic")


# ============================================================================
# 2. QUESTIONS & MEDIA
# ============================================================================

class Question(Base):
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True, index=True)
    canonical_id = Column(String(50), unique=True, index=True) # 'CQ_0385', 'ICSE10_MATH_Q001'
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("academic_classes.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)

    # Legacy / Compatibility fields
    subject_name = Column(String(100), nullable=True)
    chapter_name = Column(Text, nullable=True)
    topic_name = Column(Text, nullable=True)
    
    question_number = Column(Integer, nullable=True)
    sub_part = Column(String(10), nullable=True)             # 'i', 'ii', 'a', 'b'
    question_type = Column(String(50), nullable=False, default="short_answer") # 'mcq_single', 'numerical', 'short_answer', 'long_answer', 'case_based'
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)                    # {"A": "...", "B": "..."} or list
    correct_answer = Column(Text, nullable=True)
    solution = Column(Text, nullable=True)
    marks = Column(Numeric(4, 1), default=1.0)
    difficulty = Column(String(20), default="Medium")        # 'Easy', 'Medium', 'Hard'
    difficulty_basis = Column(String(100), nullable=True)
    
    has_diagram = Column(Boolean, default=False)
    diagram_url = Column(Text, nullable=True)                # Local relative path or cloud storage URL
    extracted_latex = Column(Text, nullable=True)
    chemical_smiles = Column(Text, nullable=True)

    source_file = Column(String(255), nullable=True)
    academic_year = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    topic = relationship("Topic", back_populates="questions")


# ============================================================================
# 3. EXAMINATION BLUEPRINTS & WEIGHTAGES
# ============================================================================

class ExaminationBlueprint(Base):
    __tablename__ = "examination_blueprints"

    id = Column(Integer, primary_key=True, index=True)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("academic_classes.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    title = Column(String(255), nullable=False)
    total_marks = Column(Numeric(5, 1), nullable=False, default=80.0)
    duration_minutes = Column(Integer, default=180)
    is_active = Column(Boolean, default=True)
    structure_config = Column(JSON, nullable=False)          # Section rules, counts, marks per q

    board = relationship("Board")
    academic_class = relationship("AcademicClass")
    subject = relationship("Subject")
    weightages = relationship("TopicWeightage", back_populates="blueprint", cascade="all, delete-orphan")


class TopicWeightage(Base):
    __tablename__ = "topic_weightages"

    id = Column(Integer, primary_key=True, index=True)
    blueprint_id = Column(Integer, ForeignKey("examination_blueprints.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    weightage_percent = Column(Numeric(5, 2), nullable=False)
    min_marks = Column(Numeric(4, 1), default=0)
    max_marks = Column(Numeric(4, 1), nullable=True)
    is_official = Column(Boolean, default=True)

    blueprint = relationship("ExaminationBlueprint", back_populates="weightages")
    chapter = relationship("Chapter")
    topic = relationship("Topic")


# ============================================================================
# 4. STUDENT PROFILES & SESSIONS
# ============================================================================

class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("academic_classes.id"), nullable=True)
    stream_id = Column(Integer, ForeignKey("academic_streams.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    board = relationship("Board")
    academic_class = relationship("AcademicClass")
    submissions = relationship("StudentSubmission", back_populates="student")
    mastery_records = relationship("StudentTopicMastery", back_populates="student")


# ============================================================================
# 5. GENERATED PAPERS & PAPERS QUESTIONS
# ============================================================================

class GeneratedPaper(Base):
    __tablename__ = "generated_papers"

    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    board_id = Column(Integer, ForeignKey("boards.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("academic_classes.id"), nullable=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    blueprint_id = Column(Integer, ForeignKey("examination_blueprints.id"), nullable=True)
    is_adaptive = Column(Boolean, default=False)
    total_marks = Column(Numeric(5, 1), nullable=False)
    duration_minutes = Column(Integer, default=180)
    created_by = Column(Integer, ForeignKey("student_profiles.id"), nullable=True)
    paper_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    board = relationship("Board")
    academic_class = relationship("AcademicClass")
    subject = relationship("Subject")
    paper_questions = relationship("PaperQuestion", back_populates="paper", cascade="all, delete-orphan")


class PaperQuestion(Base):
    __tablename__ = "paper_questions"

    id = Column(BigInteger, primary_key=True, index=True)
    paper_id = Column(BigInteger, ForeignKey("generated_papers.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(BigInteger, ForeignKey("questions.id"), nullable=False)
    section_name = Column(String(50), nullable=True)
    question_number = Column(Integer, nullable=False)
    allocated_marks = Column(Numeric(4, 1), nullable=False)

    paper = relationship("GeneratedPaper", back_populates="paper_questions")
    question = relationship("Question")


# ============================================================================
# 6. SUBMISSIONS, ANSWERS & RUBRIC EVALUATIONS
# ============================================================================

class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id = Column(BigInteger, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    paper_id = Column(BigInteger, ForeignKey("generated_papers.id", ondelete="CASCADE"), nullable=False)
    submission_type = Column(String(20), nullable=False, default="ONLINE_MCQ") # 'ONLINE_MCQ', 'WRITTEN_PDF'
    answer_sheet_url = Column(Text, nullable=True)
    total_score = Column(Numeric(5, 1), nullable=True)
    accuracy_percent = Column(Numeric(5, 2), nullable=True)
    time_taken_minutes = Column(Numeric(5, 2), nullable=True)
    status = Column(String(30), default="SUBMITTED") # 'SUBMITTED', 'EVALUATED'
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="submissions")
    paper = relationship("GeneratedPaper")
    answers = relationship("StudentAnswer", back_populates="submission", cascade="all, delete-orphan")


class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(BigInteger, primary_key=True, index=True)
    submission_id = Column(BigInteger, ForeignKey("student_submissions.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(BigInteger, ForeignKey("questions.id"), nullable=False)
    question_number = Column(Integer, nullable=True)
    student_text = Column(Text, nullable=True)
    marks_awarded = Column(Numeric(4, 1), default=0.0)
    max_marks = Column(Numeric(4, 1), nullable=False)
    is_correct = Column(Boolean, nullable=True)
    evaluator_feedback = Column(Text, nullable=True)
    rubric_evaluation = Column(JSON, nullable=True)
    needs_manual_review = Column(Boolean, default=False)

    submission = relationship("StudentSubmission", back_populates="answers")
    question = relationship("Question")


# ============================================================================
# 7. CUMULATIVE TOPIC MASTERY (ADAPTIVE ENGINE INPUT)
# ============================================================================

class StudentTopicMastery(Base):
    __tablename__ = "student_topic_mastery"

    id = Column(BigInteger, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    
    chapter_name = Column(String(255), nullable=True)
    topic_name = Column(String(255), nullable=True)

    total_attempts = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_wrong = Column(Integer, default=0)
    total_unattempted = Column(Integer, default=0)
    marks_obtained = Column(Numeric(6, 1), default=0.0)
    marks_possible = Column(Numeric(6, 1), default=0.0)
    accuracy_percentage = Column(Numeric(5, 2), default=0.0)
    mastery_status = Column(String(30), default="Not Enough Data") # 'Needs Improvement', 'Average', 'Strong'
    last_evaluated_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("StudentProfile", back_populates="mastery_records")


def init_db():
    Base.metadata.create_all(bind=engine)
    print("Database tables initialized successfully!")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
