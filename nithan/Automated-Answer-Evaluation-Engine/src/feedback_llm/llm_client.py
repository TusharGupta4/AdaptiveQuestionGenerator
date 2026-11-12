import json, logging, os, re
from typing import List

logger = logging.getLogger(__name__)
DEFAULT_MODEL_NAME = 'qwen3.8-27b'
OLLAMA_MODELS = ['qwen2.5-coder:7b', 'llama3.2:3b', 'llama3.2', 'llama2']

def _build_prompt(zero_shot: bool, score_percent: float, marks_info: str,
                  recognized_concepts: List[str], missing_keywords: List[str],
                  reference_answer: str, student_answer: str,
                  question_text: str, max_marks_value: float,
                  grade_profile=None) -> str:
    persona = (
        grade_profile['feedback_persona']
        if grade_profile else
        'You are an expert examiner providing constructive feedback.'
    )
    tone_guidance = (
        grade_profile['tone_guidance']
        if grade_profile else
        'Be constructive, specific, and appropriate for the student level.'
    )
    grade_context = (
        f"\nStudent grade band: {grade_profile['class_band']}\n"
        if grade_profile else ""
    )

    if zero_shot:
        return f"""{persona}

You are an expert evaluator grading the response directly out of {max_marks_value:g} marks.
You are performing a zero-shot assessment without any answer key or rubric ground truth.
{grade_context}
Question: {question_text[:500] if question_text else 'Evaluate the student response to the given question.'}
Student answer: {student_answer[:2000] if student_answer else '(no student answer text available)'}
Maximum marks: {max_marks_value:g}

Assess factual correctness, the number of distinct evidence points provided, completeness, logical structure, and the presence of diagrams or labelled figures. For example, a Geoid and Earth-sphericity answer should be credited for evidence such as the Bedford level experiment, the lunar eclipse shadow, ships disappearing hull-first, circumnavigation, and an accurate Geoid/spheroid diagram.

Assign estimated_marks proportionally out of {max_marks_value:g}. A detailed multi-point answer with a correct diagram should typically receive most of the available marks.

Return ONLY a valid JSON object matching this exact schema:
{{
  "estimated_marks": <number from 0 to {max_marks_value:g}>,
  "max_marks": {max_marks_value:g},
  "qualitative_feedback": "<exactly 2 complete, well-formed sentences>"
}}

Rules:
- The JSON must be directly parseable with no markdown fences, prose, or commentary outside it.
- qualitative_feedback must contain exactly two complete sentences: one explaining the marks and recognized concepts, and one giving constructive improvement advice.
- Never truncate or leave a sentence unfinished.
- Do NOT invent, assume, or hallucinate missing rubric ground truth.
- Tone requirements: {tone_guidance}

JSON:"""

    return f"""{persona}

Generate exactly 2 sentences of constructive feedback.
{grade_context}
Score: {score_percent}% {marks_info}
Recognized concepts: {', '.join(recognized_concepts) if recognized_concepts else 'Some key concepts'}
Missing/areas to improve: {', '.join(missing_keywords) if missing_keywords else 'Details and specificity'}
Reference context: {reference_answer[:150]}...
Student answer: {student_answer[:150]}...

Requirements:
- Output exactly 2 sentences
- Explain the awarded score
- Mention recognized concepts
- Suggest room for improvement
- Be constructive and specific
- Tone requirements: {tone_guidance}

Feedback:"""

def _response_text(response) -> str:
    if isinstance(response, dict):
        return str(response.get('response', '') or '').strip()
    if hasattr(response, 'response'):
        return str(response.response or '').strip()
    return str(response or '').strip()

def _parse_json_response(response_text: str):
    """Extract the first JSON object from an LLM response, including fenced JSON."""
    if not response_text:
        return None
    raw = str(response_text).strip()
    if not raw:
        return None
    cleaned = re.sub(r'```(?:json)?', '', raw, flags=re.IGNORECASE).strip()
    candidates = [raw, cleaned]
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except (TypeError, ValueError):
            continue
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, list):
            for item in payload:
                if isinstance(item, dict):
                    return item
    decoder = json.JSONDecoder()
    for candidate in candidates:
        for index, character in enumerate(candidate):
            if character != '{':
                continue
            try:
                payload, _ = decoder.raw_decode(candidate, index)
            except ValueError:
                continue
            if isinstance(payload, dict):
                return payload
    return None

def _call_groq(prompt: str, model_name: str, grade_profile=None) -> str:
    api_key = os.getenv('GROQ_API_KEY')
    if not api_key:
        return ''
    persona = (
        grade_profile['feedback_persona']
        if grade_profile else
        'You are an expert examiner.'
    )
    expects_json = (
        'estimated_marks' in prompt
        and 'qualitative_feedback' in prompt
    )
    if expects_json:
        system_prompt = (
            f"{persona} You are a strict zero-shot examiner. Return ONLY a valid "
            "JSON object with estimated_marks, max_marks and qualitative_feedback. "
            "qualitative_feedback must be exactly two complete sentences. Do not "
            "use markdown fences or add any text outside the JSON object."
        )
    else:
        system_prompt = (
            f"{persona} Give concise, specific, constructive feedback in exactly "
            "two sentences."
        )
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        request = {
            'messages': [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            'model': model_name,
            'temperature': 0.2 if expects_json else 0.3,
            'max_tokens': 700 if expects_json else 300,
        }
        if expects_json:
            request['response_format'] = {"type": "json_object"}
        completion = client.chat.completions.create(**request)
        content = ''
        if isinstance(completion, dict):
            choices = completion.get('choices') or []
            if choices:
                message = choices[0].get('message', {}) if isinstance(choices[0], dict) else getattr(choices[0], 'message', None)
                content = message.get('content', '') if isinstance(message, dict) else getattr(message, 'content', '')
        elif completion and getattr(completion, 'choices', None):
            content = getattr(completion.choices[0].message, 'content', '')
        return str(content or '').strip()
    except Exception as error:
        logger.warning("Groq inference failed (%s); falling back to local Ollama.", error)
    return ''

def _call_ollama(prompt: str) -> str:
    try:
        import ollama
    except Exception:
        return ''
    for model in OLLAMA_MODELS:
        try:
            response = ollama.generate(model=model, prompt=prompt)
            text = _response_text(response)
            if text:
                return text
        except Exception:
            continue
    return ''

def _deterministic_feedback(zero_shot: bool, score, score_percent: float,
                            marks_info: str, missing_keywords: List[str],
                            max_marks_value: float, grade_profile=None) -> str:
    grade_key = grade_profile['key'] if grade_profile else None
    if zero_shot:
        if grade_key == 'junior':
            feedback = "Good effort! "
        elif grade_key == 'senior':
            feedback = "Assessment: "
        else:
            feedback = ""
        feedback += (
            "This answer was evaluated via direct LLM zero-shot analysis without a reference answer key, "
            f"so its estimated score is out of {max_marks_value:g} marks based on factual soundness, completeness, and structure. "
        )
        if missing_keywords:
            if grade_key == 'junior':
                feedback += f"Next time, try to include ideas such as {', '.join(missing_keywords[:2])}."
            else:
                feedback += f"To improve, focus on incorporating concepts like {', '.join(missing_keywords[:2])}."
        elif grade_key == 'senior':
            feedback += "To improve, strengthen the precision and completeness of every part of the response."
        else:
            feedback += "To improve, add more specific details and ensure every part of the question is addressed."
        return feedback
    if score is not None and score >= 0.8:
        if grade_key == 'junior':
            feedback = f"Great work! You've earned {marks_info or f'{score_percent}%'} by showing a strong grasp of the key ideas. "
        elif grade_key == 'senior':
            feedback = f"Your response earns {marks_info or f'{score_percent}%'} for a technically sound treatment of the core concepts. "
        else:
            feedback = f"You've earned {marks_info or f'{score_percent}%'} by demonstrating a solid understanding of the key concepts. "
        if missing_keywords:
            feedback += f"To reach a higher score, consider elaborating on areas such as {', '.join(missing_keywords[:2])}."
        elif grade_key == 'senior':
            feedback += "Maintain this precision and support each claim with formal, exam-ready terminology."
        else:
            feedback += "Adding more specific examples would make your answer even stronger."
    elif score is not None and score >= 0.6:
        if grade_key == 'junior':
            feedback = f"Nice progress! Your work has been awarded {marks_info or f'{score_percent}%'}, and you have captured the main ideas. "
        elif grade_key == 'senior':
            feedback = f"The response has been awarded {marks_info or f'{score_percent}%'}, but the analysis requires greater technical precision. "
        else:
            feedback = f"Your work has been awarded {marks_info or f'{score_percent}%'}, showing recognition of the main ideas. "
        if missing_keywords:
            feedback += f"Room for improvement lies in covering missing concepts like {', '.join(missing_keywords[:3])} more thoroughly."
        else:
            feedback += "Try to be more precise and detailed in your explanations."
    else:
        if grade_key == 'junior':
            feedback = f"You've been awarded {marks_info or f'{score_percent}%'} as you build your understanding of this topic. "
        elif grade_key == 'senior':
            feedback = f"The response has been awarded {marks_info or f'{score_percent}%'}; it currently falls short of the required technical standard. "
        else:
            feedback = f"You've been awarded {marks_info or f'{score_percent}%'} as you build your understanding of this topic. "
        if missing_keywords:
            feedback += f"Focus on reviewing and incorporating key concepts such as {', '.join(missing_keywords[:3])} to improve your score."
        else:
            feedback += "Work on breaking down the question more systematically and providing more complete answers."
    return feedback
