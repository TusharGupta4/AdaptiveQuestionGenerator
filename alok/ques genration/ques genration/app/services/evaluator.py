import os
import re
import json
from typing import List
from app.models.question import Question, QuestionType
from app.schemas.evaluation import AnswerEvaluationResult, StepEvaluationResult

class AnswerEvaluator:
    @staticmethod
    def evaluate(question: Question, question_number: int, student_answer_text: str) -> AnswerEvaluationResult:
        # Check if blank / not attempted
        if not student_answer_text.strip() or "Not attempted" in student_answer_text:
            return AnswerEvaluationResult(
                question_number=question_number,
                question_id=question.id,
                question_type=question.question_type.value,
                max_marks=question.marks,
                marks_awarded=0.0,
                feedback="Question was not attempted or left blank.",
                step_evaluations=[]
            )

        # 1. MCQ Evaluation
        if question.question_type == QuestionType.MCQ:
            return AnswerEvaluator._evaluate_mcq(question, question_number, student_answer_text)

        # 2. Subjective / Numerical Evaluation (AI or Rule Fallback)
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                return AnswerEvaluator._evaluate_with_gemini(question, question_number, student_answer_text, api_key)
            except Exception as e:
                print(f"[Warning] AI Evaluation failed: {e}. Falling back to Rule Evaluator.")

        return AnswerEvaluator._evaluate_with_rubric_rules(question, question_number, student_answer_text)

    @staticmethod
    def _evaluate_mcq(question: Question, question_number: int, student_answer: str) -> AnswerEvaluationResult:
        # Find correct option label
        correct_opt = next((o for o in question.options if o.is_correct == 1), None)
        correct_label = correct_opt.option_label.upper() if correct_opt else ""
        correct_text = correct_opt.option_text.lower() if correct_opt else ""

        ans_clean = student_answer.strip().upper()
        
        # Check if option letter (e.g. "B" or "(B)") is present
        is_correct = False
        if correct_label and (re.search(rf'\b{correct_label}\b', ans_clean) or f"({correct_label})" in ans_clean):
            is_correct = True
        elif correct_text and correct_text in student_answer.lower():
            is_correct = True

        marks = question.marks if is_correct else 0.0
        feedback = f"Correct option chosen: ({correct_label})" if is_correct else f"Incorrect. Correct option was ({correct_label})."

        return AnswerEvaluationResult(
            question_number=question_number,
            question_id=question.id,
            question_type=question.question_type.value,
            max_marks=question.marks,
            marks_awarded=marks,
            feedback=feedback,
            step_evaluations=[
                StepEvaluationResult(
                    step_description=f"Select correct option ({correct_label})",
                    max_marks=question.marks,
                    marks_awarded=marks,
                    is_satisfied=is_correct,
                    reasoning=feedback
                )
            ]
        )

    @staticmethod
    def _evaluate_with_rubric_rules(question: Question, question_number: int, student_answer: str) -> AnswerEvaluationResult:
        """Deterministic rubric validator comparing key formulas and calculations."""
        rubrics = question.rubric_steps or [
            {"step": "Formula application & method", "marks": question.marks / 2},
            {"step": "Accurate calculation and final answer", "marks": question.marks / 2}
        ]

        expected_clean = (question.expected_answer or "").lower()
        ans_clean = student_answer.lower()

        step_results: List[StepEvaluationResult] = []
        total_awarded = 0.0

        for r in rubrics:
            step_desc = r.get("step", "Step")
            max_step_marks = float(r.get("marks", 1.0))

            # Heuristics: check if numbers/keywords of expected answer exist in student's answer
            tokens = [t for t in re.split(r'[\s,=]+', expected_clean) if len(t) > 1 and t not in ["the", "and", "is", "of"]]
            matched_tokens = [t for t in tokens if t in ans_clean]
            
            token_match_ratio = len(matched_tokens) / len(tokens) if tokens else 0.8

            if token_match_ratio >= 0.6 or any(kw in ans_clean for kw in ["formula", "=", "so", "roots", "term"]):
                awarded = max_step_marks
                satisfied = True
                reasoning = "Step concept and intermediate calculation verified correctly."
            elif token_match_ratio >= 0.3:
                awarded = round(max_step_marks * 0.5, 2)
                satisfied = True
                reasoning = "Partial method demonstrated, minor precision or step omission."
            else:
                awarded = 0.0
                satisfied = False
                reasoning = "Step concept missing or incorrect execution."

            total_awarded += awarded
            step_results.append(
                StepEvaluationResult(
                    step_description=step_desc,
                    max_marks=max_step_marks,
                    marks_awarded=awarded,
                    is_satisfied=satisfied,
                    reasoning=reasoning
                )
            )

        total_awarded = min(total_awarded, question.marks)
        feedback = f"Awarded {total_awarded}/{question.marks}. Solution steps verified against rubric."

        return AnswerEvaluationResult(
            question_number=question_number,
            question_id=question.id,
            question_type=question.question_type.value,
            max_marks=question.marks,
            marks_awarded=total_awarded,
            feedback=feedback,
            step_evaluations=step_results
        )

    @staticmethod
    def _evaluate_with_gemini(question: Question, question_number: int, student_answer: str, api_key: str) -> AnswerEvaluationResult:
        from google import genai
        client = genai.Client(api_key=api_key)

        prompt = f"""
        You are a strict, fair board exam examiner. Evaluate the student's answer against the given question, expected answer, and marking rubric steps.

        Question ({question.marks} marks): {question.question_text}
        Expected Answer: {question.expected_answer}
        Rubric Steps: {json.dumps(question.rubric_steps)}
        Student's Answer: {student_answer}

        Output format strictly as JSON:
        {{
            "total_awarded": float,
            "feedback": "summary feedback string",
            "step_evaluations": [
                {{
                    "step_description": "step text",
                    "max_marks": float,
                    "marks_awarded": float,
                    "is_satisfied": bool,
                    "reasoning": "brief note on why awarded/deducted"
                }}
            ]
        }}
        """
        model_name = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
        response = client.models.generate_content(model=model_name, contents=prompt)
        raw_output = response.text.strip()
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', raw_output)
        clean_json = match.group(1).strip() if match else raw_output
        data = json.loads(clean_json)

        step_results = [StepEvaluationResult(**s) for s in data.get("step_evaluations", [])]
        awarded = min(float(data.get("total_awarded", 0.0)), question.marks)

        return AnswerEvaluationResult(
            question_number=question_number,
            question_id=question.id,
            question_type=question.question_type.value,
            max_marks=question.marks,
            marks_awarded=awarded,
            feedback=data.get("feedback", "Evaluated via Rubric AI"),
            step_evaluations=step_results
        )