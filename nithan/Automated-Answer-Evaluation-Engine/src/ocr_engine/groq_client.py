import base64
import io
import json
import os
import re
from typing import Any, Dict, List, Optional

from PIL import Image

from .diagram_utils import (
    _append_missing_diagram_markers,
    merge_diagram_lists,
    normalize_diagrams,
    parse_inline_diagrams,
)
from .formatters import (
    _json_objects_from_text,
    normalize_formula_list,
    normalize_question_key,
    normalize_smiles,
    parse_vlm_json_output,
)

CHEMISTRY_HINTS = (
    'chem', 'chemistry', 'organic', 'inorganic', 'biochem',
    'chemical', 'molecule', 'molecular',
)


# ---------------------------------------------------------------------------
# Base64 & Subject Helpers
# ---------------------------------------------------------------------------

def image_to_base64(image: Image.Image, format: str = 'JPEG') -> str:
    """Converts a PIL Image object into a Base64 encoded string."""
    buffered = io.BytesIO()
    if image.mode != 'RGB':
        image = image.convert('RGB')
    image.save(buffered, format=format, quality=85)
    return base64.b64encode(buffered.getvalue()).decode('utf-8')


def is_chemistry_subject(
    subject_type: Optional[str] = None, subject: Optional[str] = None
) -> bool:
    """Detects whether the target paper subject involves chemical structures/SMILES."""
    combined = ' '.join(str(value or '') for value in (subject_type, subject)).lower()
    return any(hint in combined for hint in CHEMISTRY_HINTS)


# ---------------------------------------------------------------------------
# JSON Response Parsing
# ---------------------------------------------------------------------------

def _parse_json_payload(response_text: str) -> Dict[str, Any]:
    """Parses raw text or Markdown code-fence blocks into a JSON dictionary payload."""
    if not response_text:
        return {}

    raw = str(response_text).strip()
    cleaned = re.sub(r'```(?:json)?', '', raw, flags=re.IGNORECASE).strip()

    for candidate in (raw, cleaned):
        try:
            payload = json.loads(candidate)
            if isinstance(payload, dict):
                return payload
            if isinstance(payload, list) and payload and isinstance(payload[0], dict):
                return payload[0]
        except (TypeError, ValueError):
            continue

    for obj in _json_objects_from_text(cleaned):
        if isinstance(obj, dict):
            return obj

    return {}


def _extract_body_text(payload: Dict[str, Any], fallback: str = '') -> str:
    """Extracts continuous transcription text from JSON response candidate fields."""
    if isinstance(payload, dict):
        text_fields = ('student_answer', 'document_text', 'full_text', 'text', 'transcript')
        for field in text_fields:
            value = payload.get(field)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return fallback


# ---------------------------------------------------------------------------
# Groq VLM Transcription Client
# ---------------------------------------------------------------------------

def extract_with_groq(
    image: Image.Image,
    page_number: Optional[int] = None,
    total_pages: Optional[int] = None,
    prior_question_ids: Optional[List[str]] = None,
    subject_type: Optional[str] = None,
    subject: Optional[str] = None,
    include_smiles: Optional[bool] = None,
) -> Optional[Dict[str, Any]]:
    """Performs multimodal OCR transcription using Groq Vision API (qwen/qwen3.8-27b)."""
    try:
        from groq import Groq

        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return None

        if include_smiles is None:
            include_smiles = is_chemistry_subject(subject_type, subject)

        client = Groq(api_key=api_key)
        base64_image = image_to_base64(image, format='JPEG')

        if page_number is None:
            page_context = "No page context provided."
        else:
            suffix = f" of {total_pages}" if total_pages is not None else ""
            page_context = f"This is page {page_number}{suffix}."

        smiles_schema, smiles_rules = '', ''
        if include_smiles:
            smiles_schema = (
                ',\n  "smiles": ["<valid SMILES string for each chemical structure, '
                'or [] if none>"]'
            )
            smiles_rules = (
                "- CHEMISTRY MODE: for every drawn chemical structure or reaction, "
                "extract a valid canonical SMILES string into the smiles array. "
                "Include stereochemistry when visible. Return [] when no chemical "
                "structure is present or when a reliable SMILES cannot be produced.\n"
            )

        prompt = f"""You are an expert multimodal OCR and transcription engine for handwritten answer sheets.
Transcribe ALL handwritten text in this image into ONE unified continuous Markdown document.
Return ONLY a valid JSON object with this exact schema:
{{
  "student_answer": "<complete verbatim transcription in Markdown; every equation written in LaTeX>",
  "latex_formulas": ["<LaTeX equation, formula or prose surrounding without>"],
  "diagrams": [
    {{
      "figure_id": "<figure number/name if visible>",
      "description": "<what the figure shows>",
      "labels": ["<every text label printed or handwritten inside the figure>"],
      "spatial_arrangement": "<relative layout, e.g. top-to-bottom, left-to-right, arrows>",
      "relationships": ["<connections or flows between labelled parts>"]
    }}
  ]{smiles_schema}
}}

Page context: {page_context}

Strict rules:
- Write the body as GitHub-flavoured Markdown. Use headings, bullets and tables only when they reflect the answer layout.
- Write every mathematical equation and expression in LaTeX: inline as $...$ and display equations as $$...$$. Preserve operators, subscripts, superscripts, fractions, integrals and chemical equations.
- Keep equations, chemical formulas, abbreviations, and symbols verbatim. Do not correct or solve them.
- Inspect the handwritten image thoroughly. If a diagram, sketch, or map is present (e.g., Geoid diagram, orbit sketch, chemical structure), DO NOT ignore it.
- For every detected diagram, transcribe all annotations, labels, pointer arrows, and describe the diagram structure in BOTH places: 1. Add a complete diagrams entry with figure_id, description, labels, spatial_arrangement and relationships. 2. Include an inline marker in student_answer exactly in this format: [DIAGRAM_PRESENT: Title='Shape of Earth/Geoid', Labels=['North', 'South', 'Equator', 'Geoid', 'Centre of Earth mass', 'Centre of spheroid'], Description='Handwritten sketch showing oblate spheroid bulge and geoid profile relative to equator and poles']
- For every visible figure, graph, flowchart, circuit, biological drawing, map or apparatus, add one diagrams entry describing it. List every label exactly as written and state the spatial arrangement (top/bottom/left/right, rows, columns, arrows).
- Do NOT invent diagrams, labels or relationships that are not visible. Return "diagrams": [] when the page has no visual figure.
- latex_formulas must contain only the formula strings themselves, not commentary. Return [] when no formula is present.
- {smiles_rules}IGNORE printed header boxes, student registration numbers, name grids, roll numbers, assignment codes, subject/batch metadata, submission dates, page numbers, and margin notices such as "Do not write anything in this margin".
- Extract ONLY the handwritten body of the answer, including all headings, bullet points, sub-equations, and diagram labels.
- Do NOT include any form header metadata, printed instructions, or administrative notices in student_answer.
- Do NOT split the transcription into questions, answers, or numbered blocks.
- Treat numbered points such as "1.", "2.", "3.", lettered points such as "a)", "b)", bullets, sub-headings, equations, and labels as ordinary lines inside the SAME single answer.
- Never create fields such as Q1, Q2, question_number, question_id, or a list of separate question blocks.
- Never restart or invent question numbers. There is only one continuous student answer document.
- Preserve the original reading order across the whole page.
- Do not summarise, explain, correct, translate, or add commentary outside the JSON object.
- If no handwritten text is visible, return {{"student_answer": "", "latex_formulas": [], "diagrams": []{', "smiles": []' if include_smiles else ''}}}."""

        system_prompt = (
            "You are an expert multimodal OCR transcription engine for handwritten answer sheets. "
            "Ignore all printed form headers, registration numbers, name grids, assignment codes, "
            "subject/batch metadata, submission dates, and margin notices. "
            "Extract only the handwritten answer body as Markdown, with all mathematics in LaTeX. "
            "Inspect the handwritten image thoroughly. If a diagram, sketch, or map is present "
            "(e.g., Geoid diagram, orbit sketch, chemical structure), DO NOT ignore it. "
            "Transcribe all annotations, labels, pointer arrows, and describe the diagram structure "
            "in text format as an inline [DIAGRAM_PRESENT: Title='...', Labels=['...'], "
            "Description='...'] block. Also identify every diagram, its labels and its spatial "
            "arrangement in the diagrams JSON array. "
            "Return only valid JSON containing student_answer, latex_formulas and diagrams"
            + (", plus a smiles array for chemical structures. " if include_smiles else ". ")
            + "Never split the text into questions or separate blocks based on numbers, letters, "
            "bullets, or sub-headings."
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                },
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"},
        )

        text = chat_completion.choices[0].message.content
        if text and text.strip():
            payload = _parse_json_payload(text)
            body = _extract_body_text(payload, fallback=text)

            diagrams = normalize_diagrams(
                payload.get('diagrams')
                or payload.get('figures')
                or payload.get('visuals')
                or payload.get('detected_diagrams')
                or []
            )
            diagrams = merge_diagram_lists(diagrams, parse_inline_diagrams(body))
            body = _append_missing_diagram_markers(body, diagrams)

            latex_formulas = normalize_formula_list(
                payload.get('latex_formulas')
                or payload.get('latex')
                or payload.get('formulas')
                or payload.get('equations')
                or []
            )

            smiles = normalize_smiles(
                payload.get('smiles')
                or payload.get('smiles_strings')
                or payload.get('chemical_structures')
                or []
            ) if include_smiles else []

            return {
                'text': text,
                'raw_text': text,
                'full_text': text,
                'student_answer': body,
                'markdown': body,
                'unified_text': body,
                'latex_formulas': latex_formulas,
                'equations': latex_formulas,
                'formulas': latex_formulas,
                'diagrams': diagrams,
                'smiles': smiles,
                'smiles_strings': smiles,
                'chemical_structures': smiles,
                'structure': payload,
                'average_confidence': 90.0,
                'avg_confidence': 90.0,
                'confidence': 90.0,
                'confidences': [90.0],
                'is_illegible': False,
                'illegible': False,
                'below_threshold': False,
                'method': 'groq_vlm',
                'engine': 'Groq VLM (qwen/qwen3.8-27b)',
                'include_smiles': bool(include_smiles),
            }
    except Exception:
        pass

    return None


# ---------------------------------------------------------------------------
# Groq Question Segmentation
# ---------------------------------------------------------------------------

def parse_questions_with_groq(
    full_document_text: str, expected_question_ids: Optional[List[str]] = None
) -> Dict[str, str]:
    """Uses Groq to segment a continuous multi-page document into question-to-answer mappings."""
    if not full_document_text or not str(full_document_text).strip():
        return {}

    try:
        from groq import Groq

        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return {}

        expected = [
            normalize_question_key(qid)
            for qid in (expected_question_ids or [])
            if normalize_question_key(qid)
        ]
        expected_line = (
            f"Expected question IDs in this paper: {', '.join(expected)}. "
            if expected else ""
        )

        prompt = f"""You are an expert answer-sheet segmentation engine.
You are given the FULL transcription of a multi-page handwritten answer sheet, assembled in page order. Identify every question header across the ENTIRE document, such as Q1, Q2, Q3, Q4, Q5 or Question 1, Question 2, etc.
{expected_line}
Strict rules:
- A question block starts at its question header and contains ALL text after that header up to the next question header.
- Question blocks MUST span page boundaries when the answer continues onto later pages. Never cut an answer because a page ended.
- Do NOT treat numbered sub-points inside an answer (1., 2., a), b), bullets) as new questions.
- Do NOT use page numbers, page breaks, or page footers as question boundaries.
- Preserve the answer text verbatim and in reading order.
- If a question tag is genuinely absent, omit that question or return an empty string for it. Do not invent content.
- Return ONLY a valid JSON object mapping question IDs to complete answer text, for example:
  {{"Q1": "<all Q1 answer text across pages>", "Q2": "<all Q2 answer text across pages>"}}
- Use canonical IDs Q1, Q2, Q3, ... in the output.

FULL ASSEMBLED DOCUMENT:
<document>
{full_document_text}
</document>"""

        completion = Groq(api_key=api_key).chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You segment full multi-page answer-sheet transcripts by question "
                        "headers. Return only valid JSON mapping question IDs to complete "
                        "answer blocks that may span page boundaries."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            model="qwen/qwen3.8-27b",
            response_format={"type": "json_object"},
        )
        return parse_vlm_json_output(completion.choices[0].message.content)
    except Exception:
        return {}
