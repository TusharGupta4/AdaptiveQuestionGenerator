# 🎓 CollegePur: Adaptive Question Paper Generation & Assessment Ecosystem

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/frontend-Streamlit-red.svg)](https://streamlit.io/)
[![PostgreSQL](https://img.shields.io/badge/database-PostgreSQL%20%7C%20SQLite-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

An enterprise-grade, board-compliant, and pedagogically adaptive examination platform. The system unifies question paper generation, multimodal student response evaluation, scientific diagram rendering, and real-time topic mastery tracking across **CBSE, ICSE, ISC, and JEE** (Classes 9, 10, 11, 12 & Competitive).

---

## 📑 Table of Contents
1. [Project Overview & Key Features](#-project-overview--key-features)
2. [Architecture & Ecosystem Flow](#-architecture--ecosystem-flow)
3. [Prerequisites & Dependencies](#-prerequisites--dependencies)
4. [Step-by-Step Project Setup](#-step-by-step-project-setup)
5. [Environment Variables Configuration](#-environment-variables-configuration)
6. [Database Setup & Question Data Import](#-database-setup--question-data-import)
7. [Database Schema & Architecture](#-database-schema--architecture)
8. [Running the Application](#-running-the-application)
9. [Detailed Module Guide](#-detailed-module-guide)
10. [Exporting & Syncing Data](#-exporting--syncing-data)

---

## 🌟 Project Overview & Key Features

* **Multi-Board Curriculum Coverage**: Pre-configured examination blueprints and official chapter weightages for **CBSE** (Grades 9, 10, 12), **ICSE** (Grade 10), and **JEE** (Main).
* **Deterministic & Weightage-Compliant Paper Generation**: Replaces random question picking with an optimization algorithm enforcing official section structures, chapter marks targets, and cognitive difficulty splits (30% Easy, 50% Medium, 20% Hard).
* **Dynamic Adaptive Remedial Mode**: Continuously analyzes student assessment history to generate personalized diagnostic papers allocating **60% of questions to weak topics** ($<50\%$ accuracy), **25% to developing topics**, and **15% for retention**, guarded by an anti-hyperfixation 30% topic ceiling.
* **Instant Printable PDF Compilation**: Uses ReportLab to generate official examination papers formatted with institution headers, instructions, marks, and embedded vector diagrams.
* **Automated Answer Evaluation**: Supports instant grading of interactive online tests and handwritten PDFs via exact MCQ checking, floating-point numerical tolerance ($\pm 0.01$), and key-concept rubric scoring.
* **Zero-Setup Offline Portability**: Dual-engine database architecture allowing immediate out-of-the-box execution on SQLite without requiring PostgreSQL installation.

---

## 🏛 Architecture & Ecosystem Flow

```mermaid
flowchart TD
    subgraph Data Layer
        Dump["Portable Dump (data/database_dump.json)"] --> Import["Import Script (portal/scripts/import_database.py)"]
        Import --> PG[("PostgreSQL Master\ncollegepur_db")]
        Import --> SQLite[("SQLite Portable Cache\ndata/exam_engine.db")]
    end

    subgraph Core Services
        Taxonomy["Taxonomy & Blueprint Registry"]
        GenEngine["Deterministic Paper Generator Engine"]
        AdaptEngine["Adaptive Remedial Engine (60/25/15)"]
        EvalEngine["Objective & Rubric Evaluator"]
        PDFEngine["ReportLab PDF Compiler"]
    end

    subgraph Streamlit Multipage Portal
        App["app.py (Persistent Profile Selector)"]
        P1["1_Question_Bank_&_Upload.py"]
        P2["2_Exam_Paper_Generator.py"]
        P3["3_Attempt_&_Evaluate.py"]
        P4["4_Student_Analytics_Dashboard.py"]
    end

    PG --> Core Services
    SQLite --> Core Services
    Core Services --> Streamlit Multipage Portal
```

---

## 💻 Prerequisites & Dependencies

* **Python**: Version `3.10` or higher (`Python 3.12` recommended).
* **Operating System**: Windows, macOS, or Linux.
* **Git**: Installed and configured on your terminal.
* **Database (Optional)**: PostgreSQL `14+` (recommended for production) or SQLite (bundled out-of-the-box).

---

## 🚀 Step-by-Step Project Setup

### 1. Clone the Repository
```bash
git clone https://github.com/TusharGupta4/AdaptiveQuestionGenerator.git
cd AdaptiveQuestionGenerator
```

### 2. Create and Activate a Virtual Environment
```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## ⚙️ Environment Variables Configuration

Create a `.env` file in the root directory by copying the provided example:
```bash
# Windows
copy .env.example .env

# Linux / macOS
cp .env.example .env
```

### Environment Variable Reference

| Variable | Description | Default / Example Value |
| :--- | :--- | :--- |
| `DATABASE_URL` | SQLAlchemy connection string. Default uses bundled SQLite. | `sqlite:///./data/exam_engine.db` |
| `DATABASE_URL` (PostgreSQL) | For master PostgreSQL instances. | `postgresql://postgres:password@localhost:5432/collegepur_db` |
| `GEMINI_API_KEY` | Optional Google Gemini key for LLM-based descriptive evaluation. | `AIzaSy...` (Optional) |
| `GROQ_API_KEY` | Optional Groq key for ultra-fast Llama-3 rubric scoring. | `gsk_...` (Optional) |
| `OPENAI_API_KEY` | Optional OpenAI key for rubric evaluations. | `sk-...` (Optional) |

> **Note**: If `DATABASE_URL` is omitted or PostgreSQL is unreachable, the system **automatically falls back to SQLite** (`data/exam_engine.db`) without crashing!

---

## 🗄️ Database Setup & Question Data Import

The repository ships with **2,179 pre-categorized questions**, **16 blueprints**, and **334 topic weightages** in two universal formats:
1. `data/exam_engine.db` (Pre-seeded SQLite database - Zero setup required)
2. `data/database_dump.json` (Universal portable JSON dump for any database)

### Option A: Run Instantly on SQLite (Zero Setup Required)
No setup needed! The database is already pre-synced in `data/exam_engine.db`. Simply proceed to **Running the Application**.

### Option B: Import to PostgreSQL / Supabase
If you want to run against a local PostgreSQL server or a remote Supabase instance:

1. **Create the database in PostgreSQL**:
   ```sql
   CREATE DATABASE collegepur_db;
   ```
2. **Update your `.env`**:
   ```env
   DATABASE_URL=postgresql://postgres:your_password@localhost:5432/collegepur_db
   ```
3. **Execute the One-Command Import Script**:
   ```bash
   python portal/scripts/import_database.py
   ```
   *This single command initializes all 15 schemas and imports all 2,179 questions, chapters, blueprints, and weightages in under 3 seconds!*

---

## 📊 Database Schema & Architecture

The database contains **15 normalized relational tables**:

```mermaid
erDiagram
    boards ||--o{ subjects : has
    academic_classes ||--o{ subjects : has
    subjects ||--o{ chapters : contains
    chapters ||--o{ topics : contains
    chapters ||--o{ questions : categorizes
    examination_blueprints ||--o{ topic_weightages : defines
    examination_blueprints ||--o{ generated_papers : scaffolds
    generated_papers ||--o{ paper_questions : links
    questions ||--o{ paper_questions : included_in
    student_profiles ||--o{ student_submissions : attempts
    student_submissions ||--o{ student_answers : details
    student_profiles ||--o{ student_topic_mastery : tracks
```

| Table Name | Description | Key Attributes |
| :--- | :--- | :--- |
| **`boards`** | Master board entities | `code` (CBSE, ICSE, ISC, JEE), `name` |
| **`academic_classes`** | Academic grade levels | `code` (9, 10, 11, 12, JEE), `grade` |
| **`academic_streams`** | High school stream categories | `name` (General, Science, Commerce, Humanities) |
| **`subjects`** | Subjects per board & grade | `code` (e.g. `CBSE10_MATH`), `name` |
| **`chapters`** | Curriculum chapters | `chapter_code`, `name`, `chapter_number` |
| **`topics`** | Sub-topics within chapters | `topic_code`, `name` |
| **`questions`** | Master question bank | `question_text`, `options`, `correct_answer`, `solution`, `marks`, `difficulty`, `has_diagram`, `diagram_url` |
| **`examination_blueprints`**| Official paper patterns | `total_marks`, `duration_minutes`, `structure_config` |
| **`topic_weightages`** | Prescribed marks & % per chapter | `weightage_percent`, `min_marks`, `max_marks`, `is_official` |
| **`student_profiles`** | Student credentials & streams | `email`, `full_name`, `board_id`, `class_id` |
| **`generated_papers`** | Generated exam instances | `title`, `is_adaptive`, `total_marks`, `paper_metadata` |
| **`paper_questions`** | Exam question order & marks | `section_name`, `question_number`, `allocated_marks` |
| **`student_submissions`**| Test attempt records | `total_score`, `accuracy_percent`, `status` |
| **`student_answers`** | Item-level responses & feedback | `student_text`, `marks_awarded`, `evaluator_feedback` |
| **`student_topic_mastery`**| Real-time mastery metrics | `total_attempts`, `accuracy_percentage`, `mastery_status` |

---

## 🏃 Running the Application

Launch the Streamlit portal with a single command from the project root:

```bash
streamlit run portal/app.py
```

Open your browser at: **`http://localhost:8501`**

---

## 📖 Detailed Module Guide

### 1. Persistent Student Profile (`app.py`)
* Configure your **Current Grade** (`Grade 9`, `Grade 10`, `Grade 11`, `Grade 12`, or `JEE`).
* The **Preferred Board** dynamically adjusts:
  * Select `JEE` $\rightarrow$ Board dropdown is **hidden** (irrelevant for JEE).
  * Select `Grade 9` or `Grade 10` $\rightarrow$ Offers **CBSE** and **ICSE**.
  * Select `Grade 11` or `Grade 12` $\rightarrow$ Offers **CBSE** and **ISC**.
* Settings persist across all sessions; tests auto-filter to your stream.

### 2. Question Bank & Ingestion (`1_📥_Question_Bank_&_Upload.py`)
* **Explorer**: Search through all 2,179 questions with live rendering of scientific figures and math equations.
* **Dual Ingestion**:
  * **JEE Workflow**: Upload a question paper PDF $\rightarrow$ Automatic subject classification (PCM) and chapter mapping.
  * **School Workflow**: Select Grade, Board, and Subject $\rightarrow$ OCR ingestion without token waste.
* **Bulk Importer**: Download a CSV template and upload hundreds of questions in one click.

### 3. Exam Studio & Generator (`2_📝_Exam_Paper_Generator.py`)
* **Mode 1 (Blueprint Practice)**:
  * Dropdown automatically filters to display **only the blueprints matching your active profile**.
  * Deterministic optimization algorithm enforces section rules, chapter marks targets, and difficulty balance.
  * Interactive **Compliance Audit** verifies chapter marks allocation against official board weightages.
* **Mode 2 (Adaptive Remedial Practice)**:
  * Allocates **60% to weak topics**, **25% to developing topics**, and **15% for retention**.
  * Protected by a 30% topic ceiling to prevent edge-case hyperfixation.
* **Printable PDF Export**: Download formatted test papers ready for classroom distribution.

### 4. Attempt & Evaluation Hub (`3_✍️_Attempt_&_Evaluate.py`)
* **Zero Question Paper Upload Needed**: Automatically retrieves paper questions from the database.
* **Online Mode**: Interactive test taking with instant scoring.
* **Written Mode**: Upload scanned handwritten answer sheet PDFs for rubric scoring.
* Evaluates MCQs (+4 / -1 for JEE, standard positive for school), numerical tolerance ($\pm 0.01$), and keyword concept coverage.

### 5. Student Analytics Dashboard (`4_📊_Student_Analytics_Dashboard.py`)
* Real-time skill badges: 🔴 *Needs Improvement* ($<50\%$), 🟡 *Developing* ($50\%-79\%$), 🟢 *Mastered* ($\ge 80\%$).
* One-click action to immediately generate a remedial paper targeting your weak chapters.

---

## 🔄 Exporting & Syncing Data

If you add new questions or make modifications to the database:

### 1. Export Database to Portable Dump
```bash
python portal/scripts/export_database.py
```
*Exports all tables into `data/database_dump.json` (3.0 MB).*

### 2. Sync PostgreSQL to SQLite Cache
```bash
python portal/scripts/sync_local_db.py
```
*Syncs all records from PostgreSQL master into `data/exam_engine.db` for offline teammates.*

---

## 👥 Contributors & Original Modules Unified
This unified portal integrates the work of all 11 project contributors:
* **Piyush**: Official CBSE 2026-27 curriculum trees (448 units and topics).
* **Rekha**: 1,726 cleaned & classified CBSE questions.
* **Vaishnavi**: 359 ICSE Class 10 questions with 52 extracted scientific diagrams.
* **JEE Assessment Track**: JEE Physics, Chemistry, and Math weightages & +4/-1 scoring.
* **Simpi**: Handwritten OCR transcription pipeline.
* **Krishna & Alok**: Multi-agent evaluation rubrics, SymPy equations, and prompt sandboxing.
* **Nithan, Shivani & Vartika**: Blueprint structure configs, diagram bounding boxes, and PDF formatters.
