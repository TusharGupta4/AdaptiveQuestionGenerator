#!/usr/bin/env python3
"""
INTERNSHIP PROJECT: ALL CODE IN ONE FILE
========================================
AI-Powered Assessment Platform: question banks and mock-paper generation
for CBSE Class 11 (English, History, Physics).

HOW TO USE
----------
Run one part at a time from the terminal:

    python internship_project_code.py <command> [options]

Commands (in the order the work was done):

  PART 1  fix-english-data        Repair the English master dataset (Chapter / Difficulty bug)
  PART 2  train-classifiers       Train Difficulty and Question-Type classifiers (TF-IDF + Logistic Regression)
          categorize              Predict type + difficulty for one new question
  PART 3  dedup-embeddings        Sentence embeddings, near-duplicate detection, duplicate-free mock test selection
  PART 4  app                     Streamlit mock-test generator + LLM answer evaluation (see note below)
          evaluate                Grade one student answer with the LLM
  PART 5  english-pdfs-to-csv     English sample-paper PDFs -> clean question CSV
  PART 6  english-generate-paper  Generate a new English mock paper with an LLM
  PART 7  physics-pdf-to-csv      Physics sample-paper PDFs -> CSV + page images (diagrams)
  PART 8  rag-prepare             Prepare History / Physics data for RAG
          rag-index               Build the FAISS vector database (embeddings)
          rag-search              Search the question bank by meaning
          rag-generate-paper      RAG + LLM: generate a full 80-mark paper

Every command accepts --dir to point at a different working folder.
The Streamlit app is started with:   streamlit run internship_project_code.py

FOLDER LAYOUT EXPECTED (next to this file)
------------------------------------------
  English/   master_combined_chapters.csv, master_cleaned.csv, "sample paper"/*.pdf
  History/   combined_question_bank_cleaned.csv
  Physics/   the Physics sample-paper PDFs

SETUP
-----
  pip install pandas numpy scikit-learn joblib sentence-transformers faiss-cpu \
              pdfplumber python-dotenv streamlit groq openai google-generativeai
  Put API keys in a .env file next to this file:
      LLM_PROVIDER=groq            # groq | gemini | xai
      GROQ_API_KEY=...
      GEMINI_API_KEY=...
      XAI_API_KEY=...
  PDF parts need Poppler (pdftotext / pdftoppm / pdfinfo). On Windows set POPPLER_PATH
  below (or as an environment variable) to the Poppler "Library\\bin" folder.

STATUS OF EACH PART (honest summary)
------------------------------------
  Run and verified on my machine: parts 1, 2, 3, 5, 7, 8 (History + Physics RAG index/search),
  History paper generation with Gemini, English paper generation (first version) with Gemini,
  and the first Streamlit mock-test generator.
  Written but NOT yet tested against a live API: the Groq and xAI (Grok) options in llm_json(),
  the LLM answer evaluation, and Physics paper generation (Gemini free quota ran out first).
  Known limitation: part 5 extracts questions only. Matching answers from the solution pages was unreliable.
"""

import os
import re
import sys
import json
import time
import glob
import random
import pickle
import hashlib
import argparse
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd

# ============================================================================
# CONFIGURATION
# ============================================================================
BASE = Path(__file__).resolve().parent
DIRS = {
    "english": BASE / "English",
    "history": BASE / "History",
    "physics": BASE / "Physics",
}

# Poppler (needed only for the PDF parts). Change this path for your machine.
POPPLER_PATH = os.environ.get(
    "POPPLER_PATH",
    r"C:\Users\HP\Downloads\question paper\Release-26.09.0-0\poppler-26.09.0\Library\bin",
)

# Model names change often (gemini-2.0-flash was shut down while I worked), so keep them here.
GEMINI_MODEL = "gemini-3.6-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"
XAI_MODEL = "grok-4.5"  # copy the exact name from the xAI console models page

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"


def load_env():
    """Load API keys from a .env file if python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
        load_dotenv(BASE / ".env")
        load_dotenv()
    except ImportError:
        pass


def setup_poppler():
    if os.path.isdir(POPPLER_PATH) and POPPLER_PATH not in os.environ.get("PATH", ""):
        os.environ["PATH"] += os.pathsep + POPPLER_PATH


def _folder(workdir, subject):
    return Path(workdir) if workdir else DIRS[subject]


# ============================================================================
# LLM HELPER  (one place for Gemini / Groq / xAI Grok)
# ============================================================================
def _extract_json(text):
    text = text.strip().replace("```json", "").replace("```", "")
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def llm_json(prompt, max_tokens=6000, max_retries=4):
    """Send a prompt, return the reply parsed as a JSON object (or None if every retry failed).
    Provider is chosen with the LLM_PROVIDER environment variable (groq, gemini or xai)."""
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    for attempt in range(max_retries):
        try:
            if provider == "gemini":
                import google.generativeai as genai
                genai.configure(api_key=os.environ["GEMINI_API_KEY"])
                text = genai.GenerativeModel(GEMINI_MODEL).generate_content(prompt).text
            elif provider == "groq":
                from groq import Groq
                client = Groq(api_key=os.environ["GROQ_API_KEY"])
                resp = client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                text = resp.choices[0].message.content
            elif provider == "xai":
                from openai import OpenAI
                client = OpenAI(api_key=os.environ["XAI_API_KEY"], base_url="https://api.x.ai/v1")
                resp = client.chat.completions.create(
                    model=XAI_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                )
                text = resp.choices[0].message.content
            else:
                raise ValueError(f"Unknown LLM_PROVIDER '{provider}' (use groq, gemini or xai)")
            return _extract_json(text)
        except KeyError as e:
            raise RuntimeError(f"Missing environment variable {e}. Add it to your .env file.")
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate" in msg.lower() or "quota" in msg.lower():
                print(f"    Rate limit / quota hit, waiting 35s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(35)
            else:
                print(f"    LLM error: {msg[:200]} (attempt {attempt + 1}/{max_retries})")
                time.sleep(5)
    return None


def _pause_between_calls():
    """Groq's free tier limits tokens per minute, so wait a little between big requests."""
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    time.sleep({"groq": 40, "gemini": 5, "xai": 2}.get(provider, 5))


def _clean_marks(m):
    """'2 Marks (2x5=10)' -> '2' ; missing -> '0'."""
    match = re.search(r"\d+", str(m))
    return match.group() if match else "0"


# ============================================================================
# PART 1: FIX THE ENGLISH MASTER DATASET
# ----------------------------------------------------------------------------
# Problem found: master_final.csv had Chapter = "Unknown" for every row, because the
# chapter mapping ran on a file that no longer had the Source_File column.
# master_cleaned.csv has the good fine-grained Question Type; master_combined_chapters.csv
# still has Source_File. The two files are row-aligned, so Chapter is rebuilt from one and
# grafted onto the other. Difficulty is rebuilt with prefix matching (the old exact-match
# dictionary missed "Short Answer - Prose", "Long Answer - Poetry", ...).
# ============================================================================
ENGLISH_CHAPTER_MAP = {
    "Chapter1_The_Summer_of_the_Beautiful_White_Horse.csv": "Summer of the Beautiful White Horse",
    "Chapter2_The_Address.csv": "Address",
    "Chapter3_Mothers_Day.csv": "Mother's Day",
    "Chapter4_Birth.csv": "Birth",
    "Chapter5_The_Tale_of_Melon_City.csv": "Tale of Melon City",
    "Hornbill_Chapter1_Poem_A_Photograph.csv": "A Photograph",
    "Hornbill_Chapter2_Were_Not_Afraid_to_Die.csv": "We're Not Afraid to Die",
    "Hornbill_Chapter3_Discovering_Tut.csv": "Tut",
    "Hornbill_Chapter3_Poem_Laburnum_Top_Voice_of_the_Rain.csv": "Laburnum Top / Voice of the Rain",
    "Hornbill_Chapter4_Poem_Childhood.csv": "Childhood",
    "Hornbill_Chapter4_The_Ailing_Planet.csv": "Ailing Planet",
    "Hornbill_Chapter5_The_Adventure.csv": "Adventure",
    "Hornbill_Chapter6_Silk_Road.csv": "Silk Road",
    "Hornbill_Chapter6_Poem_Father_to_Son.csv": "Father to Son",
    "Class11_English_Question_Bank.csv": "Question Bank",
}


def _english_difficulty(qtype):
    q = str(qtype).lower()
    if q.startswith("very short") or q.startswith("multiple choice"):
        return "Easy"
    if q.startswith(("short answer", "assertion", "case", "match")):
        return "Medium"
    if q.startswith("long answer"):
        return "Hard"
    return "Unknown"


def part1_fix_english_master(workdir=None):
    d = _folder(workdir, "english")
    raw = pd.read_csv(d / "master_combined_chapters.csv", encoding="utf-8-sig")
    cleaned = pd.read_csv(d / "master_cleaned.csv", encoding="utf-8-sig")

    same = (raw["Question"].astype(str).str.strip().values
            == cleaned["Question"].astype(str).str.strip().values).all()
    if not same:
        raise ValueError("The two master files are not row-aligned, cannot merge them safely.")

    df = cleaned.drop(columns=["Chapter", "Difficulty"], errors="ignore").copy()
    df["Source_File"] = raw["Source_File"].values
    df["Chapter"] = df["Source_File"].apply(
        lambda x: ENGLISH_CHAPTER_MAP.get(os.path.basename(str(x)), "Unknown"))

    for col in ["Question Type", "Marks", "Question", "Answer"]:
        df[col] = df[col].astype(str).str.strip()
    df["Question Type"] = df["Question Type"].replace({"nan": "Unknown"}).str.title()
    df["Difficulty"] = df["Question Type"].apply(_english_difficulty)

    df["Answer"] = df["Answer"].replace({"nan": ""})
    df.loc[df["Answer"].str.strip() == "", "Answer"] = "Not Available"
    df["Marks"] = df["Marks"].replace({"nan": "0"})

    df = df[df["Question"].str.strip() != ""]
    df = df[["Question Type", "Marks", "Question", "Answer", "Chapter", "Difficulty"]].drop_duplicates()

    out = d / "master_fixed.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print("Saved:", out, "| shape:", df.shape)
    print("\nChapter counts:\n", df["Chapter"].value_counts())
    print("\nDifficulty counts:\n", df["Difficulty"].value_counts())
    return df


# ============================================================================
# PART 2: CLASSIFIERS  (these are the models I actually trained)
# ----------------------------------------------------------------------------
# TF-IDF + Logistic Regression. Difficulty uses question text only. Question Type
# (collapsed to 4 buckets because some of the 13 raw types had 1 example) also uses the
# Marks column, which raised macro-F1 from about 0.52 to about 0.82 in my runs.
# ============================================================================
def _coarse_type(qtype):
    q = str(qtype).lower()
    if q.startswith("very short"):
        return "Very Short Answer"
    if q.startswith("short answer"):
        return "Short Answer"
    if q.startswith("long answer"):
        return "Long Answer"
    return "Objective"  # MCQ, Assertion-Reason, Match the Following, Case-Based


def _tfidf():
    from sklearn.feature_extraction.text import TfidfVectorizer
    return TfidfVectorizer(lowercase=True, stop_words="english", ngram_range=(1, 2),
                           min_df=2, max_df=0.9, sublinear_tf=True)


def part2_train_classifiers(workdir=None):
    import joblib
    from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import classification_report, confusion_matrix, f1_score
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import OneHotEncoder

    d = _folder(workdir, "english")
    df = pd.read_csv(d / "master_fixed.csv")
    df["Coarse Type"] = df["Question Type"].apply(_coarse_type)
    df["Marks_clean"] = df["Marks"].apply(_clean_marks)
    models_dir = d / "models"
    models_dir.mkdir(exist_ok=True)

    # ---- Model 1: Difficulty from question text ----
    print("\n=== Difficulty (Easy / Medium / Hard) ===")
    print(df["Difficulty"].value_counts())
    X, y = df["Question"].astype(str), df["Difficulty"].astype(str)
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    diff_model = Pipeline([("tfidf", _tfidf()),
                           ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])
    try:
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(diff_model, X_tr, y_tr, cv=cv, scoring="f1_macro")
        print(f"CV macro-F1: {scores.mean():.3f} +/- {scores.std():.3f}")
    except ValueError as e:
        print("Skipping cross-validation:", e)
    diff_model.fit(X_tr, y_tr)
    print(classification_report(y_te, diff_model.predict(X_te), zero_division=0))
    diff_model.fit(X, y)  # refit on all data once the held-out score is trusted
    joblib.dump(diff_model, models_dir / "difficulty_classifier.joblib")

    # ---- Model 2: Question Type from text + Marks ----
    print("\n=== Question Type (4 buckets, text + marks) ===")
    print(df["Coarse Type"].value_counts())
    features = ColumnTransformer([
        ("text", _tfidf(), "Question"),
        ("marks", OneHotEncoder(handle_unknown="ignore"), ["Marks_clean"]),
    ])
    type_model = Pipeline([("features", features),
                           ("clf", LogisticRegression(max_iter=2000, class_weight="balanced"))])
    X2, y2 = df[["Question", "Marks_clean"]], df["Coarse Type"].astype(str)
    X2_tr, X2_te, y2_tr, y2_te = train_test_split(X2, y2, test_size=0.2, random_state=42, stratify=y2)
    type_model.fit(X2_tr, y2_tr)
    pred = type_model.predict(X2_te)
    print(classification_report(y2_te, pred, zero_division=0))
    print("Macro-F1 (test):", round(f1_score(y2_te, pred, average="macro"), 3))
    labels = sorted(y2.unique())
    print("Confusion matrix:\n", pd.DataFrame(confusion_matrix(y2_te, pred, labels=labels),
                                              index=labels, columns=labels))
    type_model.fit(X2, y2)
    joblib.dump(type_model, models_dir / "coarse_type_classifier_v2.joblib")
    print("\nModels saved in:", models_dir)


def categorize_question(question_text, marks_text, workdir=None, confidence_threshold=0.6):
    """Predict type + difficulty for a new question. Low-confidence type predictions are
    flagged NEEDS_REVIEW so a human can check them instead of trusting a weak guess."""
    import joblib
    models_dir = _folder(workdir, "english") / "models"
    diff_model = joblib.load(models_dir / "difficulty_classifier.joblib")
    type_model = joblib.load(models_dir / "coarse_type_classifier_v2.joblib")

    row = pd.DataFrame([{"Question": question_text, "Marks_clean": _clean_marks(marks_text)}])
    proba = type_model.predict_proba(row)[0]
    best = int(proba.argmax())
    confidence = float(proba[best])
    qtype = type_model.classes_[best] if confidence >= confidence_threshold else "NEEDS_REVIEW"
    return {
        "question_type": qtype,
        "top_guess": str(type_model.classes_[best]),
        "confidence": round(confidence, 2),
        "difficulty": str(diff_model.predict([question_text])[0]),
    }


# ============================================================================
# PART 3: EMBEDDINGS, NEAR-DUPLICATE DETECTION, DUPLICATE-FREE MOCK TESTS
# ----------------------------------------------------------------------------
# all-MiniLM-L6-v2 is a pretrained model. I did not train it, I only use it to turn each
# question into a vector so that similar meaning = high cosine similarity.
# Thresholds from my run: 0.85 -> 37 pairs, 0.90 -> 10 pairs, 0.93 -> 7 pairs, so 0.90 is used.
# ============================================================================
def embed_texts(texts, model=None):
    """Normalised embeddings, so a plain dot product equals cosine similarity."""
    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBED_MODEL_NAME)
    return np.asarray(model.encode(list(texts), show_progress_bar=True, normalize_embeddings=True),
                      dtype="float32")


def find_near_duplicates(embeddings, threshold=0.85):
    sim = embeddings @ embeddings.T
    i_idx, j_idx = np.triu_indices(len(embeddings), k=1)
    scores = sim[i_idx, j_idx]
    mask = scores >= threshold
    pairs = [(int(i), int(j), float(s)) for i, j, s in zip(i_idx[mask], j_idx[mask], scores[mask])]
    return sorted(pairs, key=lambda x: -x[2])


def remove_exact_duplicates(df, embeddings, threshold=0.999):
    """Drop exact duplicates from the table AND the embedding matrix together, so they never go out of sync."""
    sim = embeddings @ embeddings.T
    n = len(df)
    to_drop = set()
    for i in range(n):
        if i in to_drop:
            continue
        for j in range(i + 1, n):
            if sim[i, j] >= threshold:
                to_drop.add(j)
    keep = np.array([i not in to_drop for i in range(n)])
    return df[keep].reset_index(drop=True), embeddings[keep], sorted(to_drop)


def select_questions_avoiding_duplicates(df, embeddings, n_questions=10, chapter=None, difficulty=None,
                                         exclude_indices=None, similarity_threshold=0.90, seed=None):
    """Random mock test from the bank. A question is skipped if it is too similar to one already
    picked, or if the student has already seen it (exclude_indices)."""
    df = df.reset_index(drop=True)
    rng = np.random.default_rng(seed)
    exclude = set(exclude_indices or [])

    mask = pd.Series(True, index=df.index)
    if chapter:
        mask &= df["Chapter"] == chapter
    if difficulty:
        mask &= df["Difficulty"] == difficulty
    candidates = [i for i in df.index[mask] if i not in exclude]
    rng.shuffle(candidates)

    selected = []
    for idx in candidates:
        if len(selected) >= n_questions:
            break
        if not selected or (embeddings[idx] @ embeddings[selected].T).max() < similarity_threshold:
            selected.append(idx)
    return df.iloc[selected]


def part3_dedup_embeddings(workdir=None, model=None):
    d = _folder(workdir, "english")
    df = pd.read_csv(d / "master_fixed.csv")
    emb = embed_texts(df["Question"].astype(str), model)
    print("Questions:", len(df), "| embedding shape:", emb.shape)

    for t in (0.85, 0.90, 0.93):
        print(f"Threshold {t}: {len(find_near_duplicates(emb, t))} near-duplicate pairs")
    for i, j, s in find_near_duplicates(emb, 0.90)[:5]:
        print(f"\n  similarity {s:.3f}\n    A: {df.iloc[i]['Question']}\n    B: {df.iloc[j]['Question']}")

    df, emb, dropped = remove_exact_duplicates(df, emb)
    print(f"\n{len(dropped)} exact duplicate row(s) removed. New shape: {df.shape}")
    assert len(df) == emb.shape[0], "dataframe and embeddings out of sync"

    df.to_csv(d / "questions_deduped.csv", index=False, encoding="utf-8-sig")
    np.save(d / "question_embeddings.npy", emb)
    print("Saved questions_deduped.csv and question_embeddings.npy (kept in sync)")

    demo = select_questions_avoiding_duplicates(df, emb, n_questions=10, difficulty="Medium", seed=1)
    print("\nDemo mock test (Medium, 10 questions):")
    print(demo[["Question Type", "Chapter", "Question"]].to_string())


# ============================================================================
# PART 4: STREAMLIT MOCK-TEST APP + LLM ANSWER EVALUATION
# ----------------------------------------------------------------------------
# Needs the files written by part 3.  Start with:  streamlit run internship_project_code.py
# The mock-test generator was run and checked in the browser. The LLM evaluation call was
# written but I did not get to test it against a live API.
# ============================================================================
def evaluate_answer(question, reference_answer, student_answer, max_marks):
    prompt = f"""You are grading a Class 11 exam answer fairly, like a teacher.

Question: {question}
Reference answer: {reference_answer}
Maximum marks: {max_marks}
Student's answer: {student_answer}

Compare the MEANING of the student's answer with the reference (not just matching words).
Give partial marks where part of the answer is right.
Return ONLY JSON: {{"marks_awarded": <number>, "feedback": "<1-2 sentences>", "missing_points": ["..."]}}"""
    result = llm_json(prompt, max_tokens=500)
    if not result:
        raise RuntimeError("The LLM did not return a usable answer (check API key / quota).")
    return result


def streamlit_app():
    import streamlit as st

    d = DIRS["english"]
    st.set_page_config(page_title="Mock Test Generator", layout="wide")
    st.title("📚 Mock Test Generator")

    csv_path, npy_path = d / "questions_deduped.csv", d / "question_embeddings.npy"
    if not (csv_path.exists() and npy_path.exists()):
        st.error("Run `python internship_project_code.py dedup-embeddings` first.")
        st.stop()

    @st.cache_data
    def load_data():
        return pd.read_csv(csv_path), np.load(npy_path)

    df, emb = load_data()

    st.sidebar.header("Test Settings")
    chapter = st.sidebar.selectbox("Chapter", ["All"] + sorted(df["Chapter"].unique().tolist()))
    difficulty = st.sidebar.selectbox("Difficulty", ["All", "Easy", "Medium", "Hard"])
    n_questions = st.sidebar.slider("Number of Questions", 1, 20, 10)

    if st.sidebar.button("Generate Test"):
        st.session_state["test"] = select_questions_avoiding_duplicates(
            df, emb, n_questions=n_questions,
            chapter=None if chapter == "All" else chapter,
            difficulty=None if difficulty == "All" else difficulty,
            seed=random.randint(0, 10**6))

    if "test" in st.session_state:
        test = st.session_state["test"]
        st.subheader("Your Mock Test")
        for i, (_, row) in enumerate(test.iterrows(), 1):
            st.markdown(f"**Q{i}. ({row['Marks']})** {row['Question']}")

        st.divider()
        st.subheader("✍️ Try Answering a Question")
        selected_q = st.selectbox("Choose a question to answer", test["Question"].tolist())
        student_ans = st.text_area("Your Answer")
        if st.button("Submit Answer"):
            row = test[test["Question"] == selected_q].iloc[0]
            if str(row["Answer"]).strip() in ("", "Not Available"):
                st.warning("This question has no reference answer in the dataset, so it cannot be graded.")
            else:
                max_marks = _clean_marks(row["Marks"])
                with st.spinner("Evaluating..."):
                    try:
                        result = evaluate_answer(row["Question"], row["Answer"], student_ans, max_marks)
                        st.success(f"Marks awarded: {result.get('marks_awarded')} / {max_marks}")
                        st.info("Feedback: " + str(result.get("feedback", "")))
                        if result.get("missing_points"):
                            st.warning("Missing points: " + ", ".join(map(str, result["missing_points"])))
                    except Exception as e:
                        st.error(f"Evaluation failed: {e}")


# ============================================================================
# PART 5: ENGLISH SAMPLE-PAPER PDFs -> QUESTION CSV
# ----------------------------------------------------------------------------
# Pipeline: PDF -> text (pdfplumber) -> split question part / solution part -> split into
# numbered questions -> clean -> CSV.
# Two tricks that fixed real bugs:
#   * A question number is accepted only if it comes in order (1, 2, 3, ...). This ignores the
#     numbered list of General Instructions and numbered paragraphs inside reading passages.
#   * It must also have a "[marks]" bracket within the next 250 characters. This stops a numbered
#     paragraph inside a passage (for example paragraph "3." of the Ladakh passage) being taken
#     as Question 3.
# Result on my 10 papers: 150 questions (15 per paper). Answers are NOT matched to questions
# here, because the Solution section repeats the whole passage with different line breaks,
# and my matching attempts were unreliable. The split solution text is still saved.
# ============================================================================
ENGLISH_SECTION_MARKER = "SECTION A : READING SKILLS"


def _english_question_positions(text):
    section_a = text.find("SECTION A")
    if section_a == -1:
        return []
    search = text[section_a:]
    accepted, expected = [], 1
    for m in re.finditer(r"\n(\d{1,2})\.\s", search):
        num = int(m.group(1))
        if num != expected:
            continue
        if "[" in search[m.start(): m.start() + 250]:
            accepted.append((num, m.start() + section_a))
            expected += 1
    return accepted


def _english_clean(text):
    text = re.sub(r"Page \d+ of \d+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def part5_english_pdfs_to_csv(pdf_dir=None, workdir=None):
    import pdfplumber

    d = _folder(workdir, "english")
    pdf_dir = Path(pdf_dir) if pdf_dir else d / "sample paper"
    txt_dir, q_dir, s_dir = d / "extracted_text", d / "split_questions", d / "split_solutions"
    for p in (txt_dir, q_dir, s_dir):
        p.mkdir(parents=True, exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    print(f"{len(pdfs)} PDF(s) found in {pdf_dir}")

    rows = []
    for pdf_path in pdfs:
        # 1) PDF -> text
        text = ""
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
        name = pdf_path.stem + ".txt"
        (txt_dir / name).write_text(text, encoding="utf-8")

        # 2) split: the Section A heading appears twice (question part, then solution part)
        hits = [m.start() for m in re.finditer(re.escape(ENGLISH_SECTION_MARKER), text)]
        if len(hits) < 2:
            print(f"  SKIP {pdf_path.name}: section heading found {len(hits)} time(s), expected 2")
            continue
        q_text, s_text = text[:hits[1]], text[hits[1]:]
        (q_dir / name).write_text(q_text, encoding="utf-8")
        (s_dir / name).write_text(s_text, encoding="utf-8")

        # 3) numbered questions
        pos = _english_question_positions(q_text)
        for i, (num, start) in enumerate(pos):
            end = pos[i + 1][1] if i + 1 < len(pos) else len(q_text)
            block = q_text[start:end].strip()
            m = re.search(r"\[(\d+)\]", block)
            rows.append({"Source_File": name, "Q_Number": num,
                         "Marks": int(m.group(1)) if m else 0,
                         "Question_Text": _english_clean(block)})
        print(f"  {pdf_path.name}: {len(pos)} questions")

    df = pd.DataFrame(rows)
    df.to_csv(d / "questions_dataset.csv", index=False, encoding="utf-8-sig")

    final = df.copy()
    final["Paper"] = final["Source_File"].astype("category").cat.codes + 1
    final = final.rename(columns={"Source_File": "Original_File", "Q_Number": "Question_Number",
                                  "Question_Text": "Question"})
    final = final[["Paper", "Original_File", "Question_Number", "Marks", "Question"]]
    out = d / "CBSE_Class11_English_150_Questions_Cleaned.csv"
    final.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\nSaved {out.name}: {final.shape[0]} rows from {final['Paper'].nunique()} papers")
    print(final["Marks"].value_counts().sort_index())
    return final


# ============================================================================
# PART 6: GENERATE A NEW ENGLISH MOCK PAPER WITH AN LLM
# ----------------------------------------------------------------------------
# Real CBSE Class 11 English Core: 80 marks = Reading 26 + Grammar & Writing 23 + Literature 31.
# The first version I generated used very heavy vocabulary in the passages, so the prompt now
# asks for simple, Class 11 level language.
# ============================================================================
ENGLISH_BLUEPRINT = {
    "Section A: Reading Skills": {
        "total_marks": 26,
        "instructions": "Give one unseen passage (350-400 words) followed by 10 comprehension sub-questions "
                        "(mix of MCQ and short answer) worth 10 marks. Then a second shorter passage (200-250 words) "
                        "with 8 sub-questions worth 8 marks. Then a third passage with a note-making task and an "
                        "80-word summary worth 8 marks."},
    "Section B: Grammar & Writing Skills": {
        "total_marks": 23,
        "instructions": "Grammar: 7 short fill-in-the-blank / transformation questions (1 mark each, 'answer any seven'). "
                        "Writing: an advertisement or poster task (3 marks, with an OR option), a speech or debate "
                        "(5 marks, with an OR option), and another speech or debate (5 marks, with an OR option). "
                        "Adjust the grammar part so the section totals 23 marks."},
    "Section C: Literature": {
        "total_marks": 31,
        "instructions": "Poem extract with objective questions (3 marks, OR option). Prose extract with objective "
                        "questions (3 marks, OR option). Character/dialogue extract-based questions (4 marks, OR option). "
                        "Then 3 short-answer questions (3-6 marks each) from different Hornbill / Snapshots chapters "
                        "with at least one 'ANY ONE' choice, then 2 long-answer questions (6 marks each, 'ANY ONE')."},
}

ENGLISH_CHAPTERS = ("The Summer of the Beautiful White Horse, The Address, Mother's Day, Birth, The Tale of Melon City, "
                    "A Photograph, We're Not Afraid to Die, Discovering Tut, The Laburnum Top, Childhood, "
                    "The Ailing Planet, The Adventure, Silk Road, Father to Son")


def _english_section_prompt(name, info):
    return f"""You are setting a CBSE Class 11 English Core (2025-26 syllabus) mock exam paper.
Write ONLY: {name}  (total marks: {info['total_marks']}).

Instructions: {info['instructions']}

IMPORTANT: passages must use SIMPLE, CLEAR language, like a real CBSE textbook or newspaper article.
Use everyday topics (health, food, sports, environment, travel, inspiring real events). Avoid heavy academic jargon.
Literature questions must come from these chapters: {ENGLISH_CHAPTERS}.
All questions must be new and original, not copied from any existing paper.

Return ONLY valid JSON:
{{"section_title": "{name}", "questions": [{{"q_number": 1, "marks": 10,
  "question_text": "full question text with sub-parts (a), (b)... if needed",
  "answer_key": "correct answer / marking points"}}]}}"""


def _write_text_files(prefix, title, max_marks, items):
    """items: list of dicts with q_number, marks, label, question, options, answer."""
    with open(f"{prefix}.txt", "w", encoding="utf-8") as f:
        f.write("=" * 70 + f"\n{title}\nTime: 3 Hours | Maximum Marks: {max_marks}\n" + "=" * 70 + "\n")
        for q in items:
            f.write(f"\nQ{q['q_number']}. [{q['marks']} marks] {q.get('label', '')}\n{_as_text(q['question'])}\n")
            if q.get("options"):
                f.write("Options: " + _as_text(q["options"]) + "\n")
    with open(f"{prefix}_ANSWERS.txt", "w", encoding="utf-8") as f:
        for q in items:
            f.write(f"\nQ{q['q_number']}. Answer: {_as_text(q.get('answer'))}\n")


def _as_text(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return "" if value is None else str(value)


def part6_english_generate_paper(workdir=None):
    d = _folder(workdir, "english")
    items, num = [], 1
    for name, info in ENGLISH_BLUEPRINT.items():
        print(f"Generating: {name} ...")
        data = llm_json(_english_section_prompt(name, info))
        if not data:
            print("  failed, skipping this section")
            continue
        for q in data.get("questions", []):
            items.append({"q_number": num, "marks": q.get("marks", 0), "label": f"({name.split(':')[0]})",
                          "question": q.get("question_text", ""), "options": "", "answer": q.get("answer_key", "")})
            num += 1
        print(f"  -> {len(data.get('questions', []))} questions")
        _pause_between_calls()
    _write_text_files(str(d / "generated_english_paper"), "CBSE CLASS 11 ENGLISH CORE - MOCK QUESTION PAPER", 80, items)
    print("Saved generated_english_paper.txt and generated_english_paper_ANSWERS.txt in", d)


# ============================================================================
# PART 7: PHYSICS SAMPLE-PAPER PDFs -> CSV + PAGE IMAGES
# ----------------------------------------------------------------------------
# All my Physics PDFs already had a text layer, so OCR was not needed (checked with pdffonts).
# Diagrams in these PDFs are vector drawings, not embedded pictures, so pdfimages cannot extract
# them. Instead every PDF page is rendered to a PNG and each question row gets a Page_Image
# column pointing to the page where it appears.
# Result: 276 questions from 7 unique papers (8 PDFs, two were identical copies), 179 images.
# Mock 6 only has 19 of 75 answers because the source PDF itself only lists the MCQ key.
# Formulas / superscripts can come out slightly garbled: that is a limit of PDF text extraction.
# ============================================================================
PHYSICS_SECTION_MARKS = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5}
PHYSICS_SECTION_TYPE = {"A": "MCQ / Assertion-Reason", "B": "Short Answer", "C": "Short Answer (3 marks)",
                        "D": "Case Study", "E": "Long Answer"}


def _discover_physics_pdfs(pdf_dir):
    """Find Physics PDFs, name them 'Set 1', 'Mock 6' ... from the filename, skip identical copies."""
    found, seen = {}, set()
    for p in sorted(Path(pdf_dir).glob("*.pdf")):
        label = p.stem.replace("_", " ")
        if "physics" not in label.lower():
            continue
        m = re.search(r"\b(Set|Mock Paper)\s*(\d+)\b", label, flags=re.I)
        if not m:
            continue
        name = f"{'Set' if m.group(1).lower() == 'set' else 'Mock'} {m.group(2)}"
        digest = hashlib.md5(p.read_bytes()).hexdigest()
        if digest in seen:
            print(f"  skipping duplicate file: {p.name}")
            continue
        seen.add(digest)
        found.setdefault(name, p)
    return dict(sorted(found.items(), key=lambda kv: (kv[0].split()[0] != "Set", int(kv[0].split()[1]))))


def _pdf_page_texts(path):
    info = subprocess.run(["pdfinfo", str(path)], capture_output=True, encoding="utf-8", errors="ignore")
    n_pages = int(info.stdout.split("Pages:")[1].split()[0])
    pages = []
    for p in range(1, n_pages + 1):
        r = subprocess.run(["pdftotext", "-layout", "-f", str(p), "-l", str(p), str(path), "-"],
                           capture_output=True, encoding="utf-8", errors="ignore")
        pages.append((r.stdout or "").replace("\u200b", ""))
    return pages


def _physics_clean(t):
    t = re.sub(r"www\.vedantu\.com\s*\d*", " ", t)
    return re.sub(r"\s+", " ", t.replace("\f", " ")).strip()


def _sequential_positions(text, pattern):
    """Accept numbers only in order 1, 2, 3 ... (ignores numbers that appear inside a passage)."""
    out, expected = [], 1
    for m in re.finditer(pattern, text, flags=re.M):
        if int(m.group(1)) == expected:
            out.append((expected, m.start()))
            expected += 1
    return out


def _physics_questions(page_texts):
    full, page_starts = "", []
    for i, pt in enumerate(page_texts, start=1):
        page_starts.append((len(full), i))
        full += pt + "\n"

    def page_of(offset):
        page = 1
        for start, num in page_starts:
            if start <= offset:
                page = num
        return page

    sec_pos = [(m.group(1).upper(), m.start())
               for m in re.finditer(r"^\s*\f?\s*SECTION\s+([A-E])\b", full, flags=re.M | re.I)]
    start = sec_pos[0][1] if sec_pos else 0   # skip the General Instructions list
    pos = [(n, p + start) for n, p in _sequential_positions(full[start:], r"^\s*(\d{1,3})\.\s+\S")]

    rows = []
    for i, (n, p) in enumerate(pos):
        end = pos[i + 1][1] if i + 1 < len(pos) else len(full)
        block = full[p:end]
        sec = "?"
        for s, sp in sec_pos:
            if sp <= p:
                sec = s
        first_line = block.split("\n")[0]
        mm = re.search(r"\s{3,}(\d)\s*$", first_line)          # marks printed at the end of the line
        marks = int(mm.group(1)) if mm else PHYSICS_SECTION_MARKS.get(sec, 0)
        block = re.sub(r"^\s*\d{1,3}\.\s+", "", block, count=1)
        lines = block.split("\n")
        lines[0] = re.sub(r"\s{3,}\d\s*$", "", lines[0])
        rows.append({"Q_Number": n, "Section": sec, "Marks": marks,
                     "Question": _physics_clean("\n".join(lines)), "Page": page_of(p)})
    return rows


def _physics_answers(answer_text):
    """Two answer-key layouts: 'Question 1. ...' (Sets 1-5) and plain '1. ...' (Mock papers)."""
    answers = {}
    pos = [(int(m.group(1)), m.start(), m.end())
           for m in re.finditer(r"^\s*Question\s+(\d+)\.?", answer_text, flags=re.M)]
    if pos:
        for i, (n, _, e) in enumerate(pos):
            end = pos[i + 1][1] if i + 1 < len(pos) else len(answer_text)
            answers.setdefault(n, _physics_clean(answer_text[e:end]))
    else:
        pos2 = _sequential_positions(answer_text, r"^\s*(\d{1,3})\.\s+\S")
        for i, (n, p) in enumerate(pos2):
            end = pos2[i + 1][1] if i + 1 < len(pos2) else len(answer_text)
            answers[n] = _physics_clean(re.sub(r"^\s*\d{1,3}\.\s+", "", answer_text[p:end], count=1))
    return answers


def _find_page_image(img_folder, safe_name, page_num):
    """pdftoppm names files Set_1-01.png (2 digits) for long PDFs but Mock_6-1.png for short ones.
    Look at the files on disk so the CSV always holds the real filename."""
    for m in glob.glob(os.path.join(img_folder, f"{safe_name}-*.png")):
        base = os.path.basename(m)
        number = base.replace(f"{safe_name}-", "").replace(".png", "")
        if number.isdigit() and int(number) == page_num:
            return base
    return f"{safe_name}-{page_num:02d}.png"


def part7_physics_pdf_to_csv(pdf_dir=None, workdir=None):
    setup_poppler()
    d = _folder(workdir, "physics")
    d.mkdir(parents=True, exist_ok=True)
    pdf_dir = Path(pdf_dir) if pdf_dir else d
    img_folder = d / "page_images"
    img_folder.mkdir(exist_ok=True)

    papers = _discover_physics_pdfs(pdf_dir)
    if not papers:
        print("No Physics PDFs found in", pdf_dir)
        return None
    print("Papers found:", ", ".join(papers))

    rows = []
    for name, path in papers.items():
        pages = _pdf_page_texts(path)
        joined = "\f".join(pages)
        key = re.search(r"\f?\s*Answer Key", joined)
        key_page = next((i for i, t in enumerate(pages, 1) if "Answer Key" in t), None)
        q_pages = pages if key_page is None else pages[:key_page - 1] + [pages[key_page - 1].split("Answer Key")[0]]
        answers = _physics_answers(joined[key.end():] if key else "")
        questions = _physics_questions(q_pages)

        safe = name.replace(" ", "_")
        subprocess.run(["pdftoppm", "-png", "-r", "150", str(path), str(img_folder / safe)], check=True)
        for r in questions:
            r.update({"Paper": name, "Answer": answers.get(r["Q_Number"], ""),
                      "Question_Type": PHYSICS_SECTION_TYPE.get(r["Section"], ""),
                      "Page_Image": _find_page_image(str(img_folder), safe, r["Page"])})
            rows.append(r)
        missing = sum(1 for r in questions if not r["Answer"])
        print(f"{name}: {len(questions)} questions, {len(answers)} answers (missing: {missing})")

    cols = ["Paper", "Q_Number", "Section", "Question_Type", "Marks", "Page", "Page_Image", "Question", "Answer"]
    df = pd.DataFrame(rows)[cols]
    df.to_csv(d / "physics_questions_with_images.csv", index=False, encoding="utf-8-sig")
    print(f"\nDONE: {len(df)} questions, {len(glob.glob(str(img_folder / '*.png')))} page images in {img_folder}")
    return df


# ============================================================================
# PART 8: RAG (History and Physics)  = embeddings + FAISS search + LLM generation
# ----------------------------------------------------------------------------
# Retrieval: every question is embedded (pretrained MiniLM, no training) and stored in a FAISS index.
# Generation: for each section the code picks topics, retrieves the most similar real questions of
# that type from the index, and shows them to the LLM as style / difficulty examples. The LLM writes
# NEW questions. No model is trained here; RAG and prompting are enough for 150-300 questions.
# The first English RAG scripts (prepare / create embeddings / retrieve) were written by a teammate.
# I reviewed them (dropped the boilerplate text from the embedded document, replaced placeholder
# labels with real ones) and adapted them for History and Physics.
# Note: the History paper I generated earlier used randomly chosen examples. The topic-similarity
# retrieval below is the improved version I wrote for Physics, now used for both.
# ============================================================================
SUBJECTS = {
    "history": {
        "dir": DIRS["history"],
        "source_csv": "combined_question_bank_cleaned.csv",
        "rag_csv": "data/rag_history_questions.csv",
        "vector_dir": "rag/vector_store_history",
        "group_col": "question_type",
        "exam": "CBSE Class 11 History (Themes in World History)",
        "output_prefix": "generated_history_paper",
        "blueprint": [
            {"group": "Mcq", "label": "MCQ", "count": 12, "marks": 1, "n_topics": 6},
            {"group": "Source-Based", "label": "Source-Based", "count": 3, "marks": 4, "n_topics": 3},
            {"group": "Short Answer", "label": "Short Answer", "count": 8, "marks": 3, "n_topics": 5},
            {"group": "Long Answer Type Questions", "label": "Long Answer", "count": 4, "marks": 8, "n_topics": 4},
        ],
        "rules": {
            "Mcq": "Each MCQ has four options a)-d); put them in 'options'. The answer is the correct option with a one-line reason.",
            "Source-Based": "Each question gives a short historical source (a quote or passage) followed by 3 sub-questions (1.1, 1.2, 1.3). Put everything in 'question'.",
            "Short Answer": "Each question needs a short answer of about 3 sentences.",
            "Long Answer Type Questions": "Each question has two parts (a) and (b). Every part must be a complete instruction sentence, "
                                          "never just a bracketed topic label like '[PART (a): Topic]'.",
        },
        "topics": ["Roman Empire administration", "Rise of Islam", "China imperial system", "Renaissance humanism",
                   "Protestant Reformation", "Crusades", "Ottoman Empire", "Feudalism in Europe", "Byzantine Empire",
                   "Trade in medieval world", "Mongol conquests", "European exploration"],
    },
    "physics": {
        "dir": DIRS["physics"],
        "source_csv": "physics_questions_with_images.csv",
        "rag_csv": "data/rag_physics_questions.csv",
        "vector_dir": "rag/vector_store_physics",
        "group_col": "Section",
        "exam": "CBSE Class 11 Physics",
        "output_prefix": "generated_physics_paper",
        "blueprint": [
            {"group": "A", "label": "Section A", "count": 18, "marks": 1, "n_topics": 6},
            {"group": "B", "label": "Section B", "count": 7, "marks": 2, "n_topics": 5},
            {"group": "C", "label": "Section C", "count": 7, "marks": 3, "n_topics": 5},
            {"group": "D", "label": "Section D", "count": 3, "marks": 4, "n_topics": 3},
            {"group": "E", "label": "Section E", "count": 3, "marks": 5, "n_topics": 3},
        ],
        "rules": {
            "A": "MCQs with four options (a)-(d). Out of the 18 questions, make 4 of them Assertion-Reason type (with the standard four options).",
            "B": "Short conceptual or one-step numerical questions answerable in 2-3 lines.",
            "C": "Conceptual or numerical questions needing a short derivation or 3-4 steps. Give the full solution.",
            "D": "Each question is a case study: a 60-100 word real-life passage followed by 4 sub-questions (a)-(d) of 1 mark each. "
                 "Put the passage and all sub-questions together in the 'question' field.",
            "E": "Long answer questions (derivations or detailed numericals with parts (a) and (b)). Give the full answer.",
        },
        "topics": ["Units and measurements", "Motion in a straight line", "Motion in a plane", "Laws of motion",
                   "Work energy and power", "System of particles and rotational motion", "Gravitation",
                   "Mechanical properties of solids", "Mechanical properties of fluids",
                   "Thermal properties of matter", "Thermodynamics", "Kinetic theory of gases", "Oscillations", "Waves"],
    },
}


def _prepare_history(d):
    df = pd.read_csv(d / SUBJECTS["history"]["source_csv"])
    df["Marks_Clean"] = df["Marks"].apply(lambda m: int(_clean_marks(m)))
    df["question_id"] = [f"HQ{i:03d}" for i in range(1, len(df) + 1)]
    df["class"], df["subject"] = 11, "History"
    df["question_type"] = df["Question Type"]

    def difficulty(qtype):
        q = str(qtype).lower()
        if q == "mcq":
            return "Easy"
        if q in ("short answer", "source-based"):
            return "Medium"
        return "Hard" if "long answer" in q else "Unknown"

    df["difficulty"] = df["question_type"].apply(difficulty)
    # only the real question text (and options) is embedded: constant metadata would just add noise
    df["document"] = df.apply(lambda r: str(r["Question"]) + (
        "\nOptions: " + str(r["Options"]) if pd.notna(r.get("Options")) else ""), axis=1)
    return df


def _prepare_physics(d):
    df = pd.read_csv(d / SUBJECTS["physics"]["source_csv"])
    df["question_id"] = [f"PQ{i:03d}" for i in range(1, len(df) + 1)]
    df["class"], df["subject"] = 11, "Physics"
    df["question_type"] = df["Question_Type"]
    df["difficulty"] = df["Section"].map(lambda s: {"A": "Easy", "B": "Medium", "C": "Medium",
                                                    "D": "Hard", "E": "Hard"}.get(str(s).upper(), "Unknown"))
    df["document"] = df["Question"].astype(str)
    return df


def rag_prepare(subject, workdir=None):
    cfg = SUBJECTS[subject]
    d = _folder(workdir, subject)
    df = _prepare_history(d) if subject == "history" else _prepare_physics(d)
    out = d / cfg["rag_csv"]
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print("Saved:", out, "| shape:", df.shape)
    print(df[cfg["group_col"]].value_counts())
    print(df["difficulty"].value_counts())
    return df


def rag_build_index(subject, workdir=None, model=None):
    import faiss
    cfg = SUBJECTS[subject]
    d = _folder(workdir, subject)
    df = pd.read_csv(d / cfg["rag_csv"])
    documents = df["document"].fillna("").tolist()

    if model is None:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBED_MODEL_NAME)
    embeddings = np.asarray(model.encode(documents, convert_to_numpy=True, show_progress_bar=True), dtype="float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    vdir = d / cfg["vector_dir"]
    vdir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(vdir / "questions.index"))
    with open(vdir / "metadata.pkl", "wb") as f:
        pickle.dump({"question_ids": df["question_id"].tolist(), "documents": documents, "dataframe": df}, f)
    print(f"Vector database created: {index.ntotal} vectors, dimension {embeddings.shape[1]} -> {vdir}")


class RagStore:
    """Loads the FAISS index + question table and offers search and example retrieval."""

    def __init__(self, subject, workdir=None, model=None):
        import faiss
        self.cfg = SUBJECTS[subject]
        vdir = _folder(workdir, subject) / self.cfg["vector_dir"]
        self.index = faiss.read_index(str(vdir / "questions.index"))
        with open(vdir / "metadata.pkl", "rb") as f:
            self.df = pickle.load(f)["dataframe"]
        if model is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(EMBED_MODEL_NAME)
        self.model = model

    def _query_vector(self, text):
        return np.asarray(self.model.encode([text], convert_to_numpy=True), dtype="float32")

    def search(self, query, k=5):
        distances, indices = self.index.search(self._query_vector(query), k)
        results = []
        for rank, (idx, dist) in enumerate(zip(indices[0], distances[0]), start=1):
            row = self.df.iloc[idx]
            results.append({"rank": rank, "question_id": row["question_id"],
                            "type": row["question_type"], "distance": float(dist), "question": row["Question"]})
        return results

    def examples(self, group_value, topics, per_topic=1):
        """For each topic, the most similar real questions of this type (the 'R' in RAG)."""
        out, seen = [], set()
        col = self.cfg["group_col"]
        for topic in topics:
            _, idxs = self.index.search(self._query_vector(topic), self.index.ntotal)
            got = 0
            for i in idxs[0]:
                row = self.df.iloc[i]
                if str(row[col]) != str(group_value) or i in seen:
                    continue
                seen.add(i)
                out.append({"question": str(row["Question"])[:700], "answer": str(row.get("Answer", ""))[:400]})
                got += 1
                if got >= per_topic:
                    break
        return out


def _rag_batch_prompt(cfg, section, topics, examples):
    examples_text = "\n\n".join(f"Example question: {e['question']}\nExample answer: {e['answer']}" for e in examples)
    return f"""You are an experienced paper-setter for {cfg['exam']}.

Create {section['count']} NEW, original questions of type "{section['label']}", {section['marks']} mark(s) each.
Cover these topics: {", ".join(topics)}.

Type rules: {cfg['rules'][section['group']]}

General rules:
- Write every question in clear English as a complete sentence with a command word (State, Explain, Discuss, Calculate, ...). Never write only a topic name or a heading.
- No question may depend on a figure, graph or diagram, because the paper is text-only.
- For numericals, give the full step-by-step solution in the answer.
- The questions must be different from the reference examples below. Use the examples only for style and difficulty.

Reference examples:
{examples_text}

Return ONLY a JSON object:
{{"questions": [{{"question": "...", "options": "(a) ... (b) ... (c) ... (d) ... for MCQ, otherwise an empty string", "answer": "..."}}]}}"""


def rag_generate_paper(subject, workdir=None, store=None):
    cfg = SUBJECTS[subject]
    d = _folder(workdir, subject)
    store = store or RagStore(subject, workdir)
    items, num = [], 1
    blueprint = cfg["blueprint"]
    for i, section in enumerate(blueprint):
        print(f"\nGenerating {section['count']} x {section['label']} ({section['marks']} marks each)...")
        topics = random.sample(cfg["topics"], section["n_topics"])
        data = llm_json(_rag_batch_prompt(cfg, section, topics, store.examples(section["group"], topics)))
        batch = (data or {}).get("questions", [])
        for q in batch[:section["count"]]:
            items.append({"q_number": num, "marks": section["marks"], "label": f"({section['label']})",
                          "question": q.get("question", ""), "options": q.get("options", ""),
                          "answer": q.get("answer", "")})
            num += 1
        print(f"  -> {len(batch)} questions received (needed {section['count']})")
        if i < len(blueprint) - 1:
            _pause_between_calls()
    total = sum(q["marks"] for q in items)
    _write_text_files(str(d / cfg["output_prefix"]), f"{cfg['exam'].upper()} - MOCK QUESTION PAPER", 80, items)
    print(f"\nDone. {len(items)} questions, {total} marks. Saved {cfg['output_prefix']}.txt and _ANSWERS.txt in {d}")
    if total != 80:
        print("Warning: total is not 80, some batches were incomplete. Run again or check the output.")


# ============================================================================
# COMMAND LINE
# ============================================================================
def main():
    load_env()
    parser = argparse.ArgumentParser(description="Internship project: all code in one file")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def add(name, help_, subject=False, pdf=False, extra=()):
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("--dir", help="working folder (default: the subject folder next to this file)")
        if pdf:
            sp.add_argument("--pdf-dir", help="folder that holds the PDFs")
        if subject:
            sp.add_argument("--subject", required=True, choices=sorted(SUBJECTS))
        for a in extra:
            sp.add_argument(*a[0], **a[1])
        return sp

    add("fix-english-data", "PART 1: repair the English master dataset")
    add("train-classifiers", "PART 2: train Difficulty and Question-Type classifiers")
    add("categorize", "PART 2: predict type + difficulty of one question", extra=[
        (["--question"], {"required": True}), (["--marks"], {"default": "2"})])
    add("dedup-embeddings", "PART 3: embeddings, duplicate detection, mock-test demo")
    add("app", "PART 4: how to start the Streamlit app")
    add("evaluate", "PART 4: grade one student answer with the LLM", extra=[
        (["--question"], {"required": True}), (["--reference"], {"required": True}),
        (["--answer"], {"required": True}), (["--marks"], {"default": "3"})])
    add("english-pdfs-to-csv", "PART 5: English PDFs -> question CSV", pdf=True)
    add("english-generate-paper", "PART 6: generate a new English paper with the LLM")
    add("physics-pdf-to-csv", "PART 7: Physics PDFs -> CSV + page images", pdf=True)
    add("rag-prepare", "PART 8: prepare RAG data", subject=True)
    add("rag-index", "PART 8: build the FAISS vector database", subject=True)
    add("rag-search", "PART 8: search the question bank", subject=True, extra=[
        (["--query"], {"required": True}), (["--k"], {"type": int, "default": 5})])
    add("rag-generate-paper", "PART 8: RAG + LLM full paper", subject=True)

    a = parser.parse_args()
    if a.cmd == "fix-english-data":
        part1_fix_english_master(a.dir)
    elif a.cmd == "train-classifiers":
        part2_train_classifiers(a.dir)
    elif a.cmd == "categorize":
        print(categorize_question(a.question, a.marks, a.dir))
    elif a.cmd == "dedup-embeddings":
        part3_dedup_embeddings(a.dir)
    elif a.cmd == "app":
        print("Start the app with:\n    streamlit run internship_project_code.py")
    elif a.cmd == "evaluate":
        print(json.dumps(evaluate_answer(a.question, a.reference, a.answer, a.marks), indent=2))
    elif a.cmd == "english-pdfs-to-csv":
        part5_english_pdfs_to_csv(a.pdf_dir, a.dir)
    elif a.cmd == "english-generate-paper":
        part6_english_generate_paper(a.dir)
    elif a.cmd == "physics-pdf-to-csv":
        part7_physics_pdf_to_csv(a.pdf_dir, a.dir)
    elif a.cmd == "rag-prepare":
        rag_prepare(a.subject, a.dir)
    elif a.cmd == "rag-index":
        rag_build_index(a.subject, a.dir)
    elif a.cmd == "rag-search":
        for r in RagStore(a.subject, a.dir).search(a.query, a.k):
            print(f"\nRank {r['rank']} | {r['question_id']} | {r['type']} | distance {r['distance']:.3f}\n{r['question'][:400]}")
    elif a.cmd == "rag-generate-paper":
        rag_generate_paper(a.subject, a.dir)


def _running_in_streamlit():
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        return get_script_run_ctx() is not None
    except Exception:
        return False


if __name__ == "__main__":
    if _running_in_streamlit():
        load_env()
        streamlit_app()
    else:
        main()
