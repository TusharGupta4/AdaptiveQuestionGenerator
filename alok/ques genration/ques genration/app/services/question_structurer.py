import os
import re
import json
from typing import List
from app.core.config import settings
from app.schemas.extraction import ExtractedPaper, ExtractedQuestion, ExtractedOption

class QuestionStructurer:
    @staticmethod
    def parse_paper(raw_text: str) -> ExtractedPaper:
        """
        Tries to use Gemini API if GEMINI_API_KEY is configured,
        otherwise seamlessly falls back to high-accuracy Regex/Rule Parser.
        """
        api_key = os.getenv("GEMINI_API_KEY") or getattr(settings, "GEMINI_API_KEY", None)
        if api_key:
            try:
                return QuestionStructurer._parse_with_gemini(raw_text, api_key)
            except Exception as e:
                print(f"[Warning] LLM parsing failed ({e}). Falling back to Rule Parser.")

        return QuestionStructurer._parse_with_rules(raw_text)

    @staticmethod
    def _parse_with_rules(raw_text: str) -> ExtractedPaper:
        """Rule-based extractor for standard structured test papers."""
        questions: List[ExtractedQuestion] = []
        
        # Regex to split on patterns like "Q1.", "Q2.", "Q1", "1.", "2."
        pattern = r'(?:^|\n)(?:Q\.?\s*(\d+)\.?|\b(\d+)\.)\s+'
        splits = re.split(pattern, raw_text)
        
        # Extract headers if available
        subject = "Mathematics"
        grade = "Class 10"
        if "Class" in raw_text:
            grade_match = re.search(r'Class\s*(\d+)', raw_text, re.IGNORECASE)
            if grade_match:
                grade = f"Class {grade_match.group(1)}"

        # Iterate through splits
        i = 1
        while i < len(splits):
            q_num = splits[i] or splits[i+1]
            content = splits[i+2] if (i+2) < len(splits) else ""
            i += 3
            
            if not content.strip():
                continue

            lines = [line.strip() for line in content.strip().split("\n") if line.strip()]
            q_text_lines = []
            options: List[ExtractedOption] = []
            marks = 1.0
            difficulty = "MEDIUM"
            q_type = "SHORT"
            expected_answer = ""
            rubric_steps = []
            suggested_topic = "General"
            suggested_chapter = "Mathematics"

            # Parse lines of the question block
            for line in lines:
                # Detect Marks: e.g. [Marks: 2] or (2 Marks) or [2]
                mark_match = re.search(r'\[(?:Marks:\s*)?(\d+(?:\.\d+)?)\]|\((\d+(?:\.\d+)?)\s*Marks?\)', line, re.IGNORECASE)
                if mark_match:
                    marks = float(mark_match.group(1) or mark_match.group(2))
                    continue

                # Detect Topic tag: e.g. [Topic: Nature of Roots]
                topic_match = re.search(r'\[Topic:\s*(.*?)\]', line, re.IGNORECASE)
                if topic_match:
                    suggested_topic = topic_match.group(1).strip()
                    continue

                # Detect Chapter tag: e.g. [Chapter: Quadratic Equations]
                chap_match = re.search(r'\[Chapter:\s*(.*?)\]', line, re.IGNORECASE)
                if chap_match:
                    suggested_chapter = chap_match.group(1).strip()
                    continue

                # Detect Answer tag: e.g. [Answer: x = 2]
                ans_match = re.search(r'\[Answer:\s*(.*?)\]', line, re.IGNORECASE)
                if ans_match:
                    expected_answer = ans_match.group(1).strip()
                    continue

                # Detect Options: (A) Option text or A. Option text
                opt_match = re.match(r'^\(?([A-D])\)?[.\- ]\s*(.*)', line)
                if opt_match:
                    opt_label = opt_match.group(1).upper()
                    opt_text = opt_match.group(2).strip()
                    is_corr = (opt_label in expected_answer.upper()) if expected_answer else False
                    options.append(ExtractedOption(label=opt_label, text=opt_text, is_correct=is_corr))
                    q_type = "MCQ"
                    continue

                q_text_lines.append(line)

            full_q_text = " ".join(q_text_lines)

            # Determine Question Type & Difficulty based on marks & structure
            if options:
                q_type = "MCQ"
                marks = 1.0
                difficulty = "EASY"
            elif marks >= 4.0:
                q_type = "LONG"
                difficulty = "HARD"
            elif any(c in full_q_text.lower() for c in ["find the value", "calculate", "solve"]):
                q_type = "NUMERICAL" if marks <= 3.0 else "LONG"
            else:
                q_type = "SHORT"

            # Generate default rubric if not provided
            rubric_steps = [
                {"step": "Initial formula / setup", "marks": round(marks * 0.4, 1)},
                {"step": "Correct calculation and final result", "marks": round(marks * 0.6, 1)}
            ]

            questions.append(ExtractedQuestion(
                question_text=full_q_text,
                question_type=q_type,
                marks=marks,
                difficulty=difficulty,
                expected_answer=expected_answer or "Refer to marking scheme",
                rubric_steps=rubric_steps,
                suggested_chapter=suggested_chapter,
                suggested_topic=suggested_topic,
                suggested_subtopic=None,
                options=options if options else None,
                source="Extracted Paper"
            ))

        return ExtractedPaper(subject=subject, grade=grade, questions=questions)

    @staticmethod
    def _parse_with_gemini(raw_text: str, api_key: str) -> ExtractedPaper:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        You are an expert exam question parser. Extract questions from the following text and convert them into the given JSON format:
        {{
            "subject": "Mathematics",
            "grade": "Class 10",
            "questions": [
                {{
                    "question_text": "...",
                    "question_type": "MCQ" | "SHORT" | "LONG" | "NUMERICAL",
                    "marks": 2.0,
                    "difficulty": "EASY" | "MEDIUM" | "HARD",
                    "expected_answer": "...",
                    "rubric_steps": [{{"step": "...", "marks": 1.0}}],
                    "suggested_chapter": "...",
                    "suggested_topic": "...",
                    "suggested_subtopic": "...",
                    "options": [{{"label": "A", "text": "...", "is_correct": false}}]
                }}
            ]
        }}
        Raw text to extract:
        {raw_text}
        Return ONLY valid JSON.
        """
        response = client.models.generate_content(
            model=os.getenv('GEMINI_MODEL', 'gemini-3.8-flash'),
            contents=prompt,
        )
        raw_output = response.text.strip()
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_output)
        clean_json = match.group(1).strip() if match else raw_output
        data = json.loads(clean_json)
        return ExtractedPaper(**data)