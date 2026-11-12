import json

import groq
from PIL import Image, ImageDraw, ImageFont

from src import ocr_engine


def test_confidence_output():
    """Test that confidence scores are returned and illegible flag works"""
    # Create a simple image with text
    img = Image.new('RGB', (200, 50), color='white')
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    draw.text((10, 10), "Hello World", fill='black', font=font)
    
    result = ocr_engine.extract_text_with_confidence(img)
    assert isinstance(result, dict)
    # Check for confidence
    assert 'average_confidence' in result or 'confidence' in result or 'avg_confidence' in result
    # Check for illegible flag
    assert 'is_illegible' in result or 'illegible' in result or 'below_threshold' in result
    
    conf = result.get('average_confidence', result.get('confidence', result.get('avg_confidence', 0)))
    assert isinstance(conf, (int, float))
    assert conf >= 0  # confidence is percentage


def test_illegible_flag_below_40():
    """Test that text below 40% confidence is flagged as illegible"""
    # Create a very noisy/illegible image
    img = Image.new('RGB', (100, 30), color='white')
    draw = ImageDraw.Draw(img)
    # Add random noise-like pattern
    for i in range(0, 100, 2):
        draw.point((i, 15), fill='black')
    
    result = ocr_engine.extract_text_with_confidence(img)
    conf = result.get('average_confidence', result.get('confidence', result.get('avg_confidence', 100)))
    is_illegible = result.get('is_illegible', result.get('illegible', result.get('below_threshold', False)))
    # If confidence is below 40, should be flagged
    if conf < 40:
        assert is_illegible is True


def test_regex_parsing_question_headers():
    """Test regex parsing for question headers like Q1:, Ans 1:, 1."""
    text = """
    Q1: What is the capital of France?
    Answer: Paris
    
    Q2: Explain photosynthesis.
    Ans 1: Plants use sunlight to convert CO2 and water.
    
    1. What is 2+2?
    2. What is the speed of light?
    """
    
    headers = ocr_engine.parse_question_headers(text)
    assert isinstance(headers, list)
    assert len(headers) > 0
    
    # Check that we found Q patterns
    q_found = any('Q' in str(h.get('match', h.get('full_match', ''))).upper() or 
                  h.get('type') in ['question', 'question_header'] or
                  h.get('number') for h in headers)
    assert q_found


def test_normalize_multimodal_diagram_payload():
    """Diagram records expose labels, spatial arrangement and page-safe defaults."""
    diagrams = ocr_engine.normalize_diagrams({
        'diagrams': [
            {
                'figure_id': 'Fig 2',
                'description': 'Water cycle',
                'labels_present': 'Evaporation, Condensation',
                'spatial_arrangement': 'circular, clockwise',
                'relationships': 'evaporation -> condensation',
            },
        ]
    })

    assert len(diagrams) == 1
    assert diagrams[0]['figure_id'] == 'Fig 2'
    assert diagrams[0]['labels'] == ['Evaporation', 'Condensation']
    assert diagrams[0]['labels_present'] == ['Evaporation', 'Condensation']
    assert 'clockwise' in diagrams[0]['spatial_arrangement']
    assert ocr_engine.extract_diagram_labels(diagrams) == [
        'Evaporation',
        'Condensation',
    ]


def test_parse_inline_diagram_marker_preserves_nested_label_list():
    text = (
        "The Earth is an oblate spheroid.\n"
        "[DIAGRAM_PRESENT: Title='Shape of Earth/Geoid', "
        "Labels=['North', 'South', 'Equator', 'Geoid', 'Centre of Earth's mass'], "
        "Description='Handwritten sketch showing the geoid profile', "
        "SpatialArrangement='Poles top and bottom, equator across the middle']"
    )

    diagrams = ocr_engine.parse_inline_diagrams(text)

    assert len(diagrams) == 1
    assert diagrams[0]['figure_id'] == 'Shape of Earth/Geoid'
    assert diagrams[0]['labels'] == [
        'North', 'South', 'Equator', 'Geoid', "Centre of Earth's mass"
    ]
    assert 'geoid profile' in diagrams[0]['description'].lower()
    assert 'equator' in diagrams[0]['spatial_arrangement'].lower()


def test_groq_prompt_requests_diagrams_and_parses_inline_output(monkeypatch):
    captured = {}
    response_text = json.dumps({
        'student_answer': (
            "The Earth is an oblate spheroid.\n"
            "[DIAGRAM_PRESENT: Title='Shape of Earth/Geoid', "
            "Labels=['North', 'South', 'Equator', 'Geoid'], "
            "Description='Geoid sketch with polar flattening']"
        ),
        'latex_formulas': [],
        'diagrams': [],
    })

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return type('Completion', (), {
                'choices': [
                    type('Choice', (), {
                        'message': type('Message', (), {'content': response_text})()
                    })()
                ]
            })()

    class FakeGroq:
        def __init__(self, api_key):
            self.chat = type('Chat', (), {'completions': FakeCompletions()})()

    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setattr(groq, 'Groq', FakeGroq)

    result = ocr_engine.extract_with_groq(
        Image.new('RGB', (20, 20), color='white'),
        subject='Geography',
    )

    system_prompt = captured['messages'][0]['content']
    user_prompt = captured['messages'][1]['content'][0]['text']
    assert 'Inspect the handwritten image thoroughly' in system_prompt
    assert 'DIAGRAM_PRESENT' in system_prompt
    assert 'DIAGRAM_PRESENT' in user_prompt
    assert captured['model'] == 'qwen/qwen3.8-27b'
    assert captured['response_format'] == {'type': 'json_object'}
    assert result['diagrams'][0]['labels'] == [
        'North', 'South', 'Equator', 'Geoid'
    ]
    assert '[DIAGRAM_PRESENT' in result['student_answer']


def test_chemistry_subject_enables_smiles_extraction():
    assert ocr_engine.is_chemistry_subject(subject='Chemistry')
    assert ocr_engine.is_chemistry_subject(subject_type='organic chemistry')
    assert not ocr_engine.is_chemistry_subject(subject='History')
    assert ocr_engine.normalize_smiles('CCO, c1ccccc1') == ['CCO', 'c1ccccc1']


def test_parse_vlm_json_output_normalizes_and_groups():
    """Structured VLM JSON should normalize keys and fold orphan sub-points into parent questions"""
    import json

    payload = json.dumps({
        'answers': [
            {'question_number': 'Question 1', 'extracted_text': 'Photosynthesis definition INPUTS sunlight water OUTPUTS glucose oxygen'},
            {'question_number': 'e)', 'extracted_text': '6CO2 + 6H2O -> C6H12O6 + 6O2'},
            {'question_number': '2.', 'extracted_text': "Newton's Second Law defines force"},
            {'question_number': 'q2', 'extracted_text': 'F = ma and a football example'},
        ]
    })

    result = ocr_engine.parse_vlm_json_output(payload)

    assert set(result.keys()) == {'Q1', 'Q2'}
    assert 'Photosynthesis definition' in result['Q1']
    assert '6CO2 + 6H2O' in result['Q1']
    assert "Newton's Second Law" in result['Q2']
    assert 'F = ma' in result['Q2']


def test_parse_vlm_json_output_multiple_pages_and_fences():
    """Concatenated fenced JSON page payloads should merge into one question map"""
    text = (
        '```json\n{"answers":[{"question_number":"1)","extracted_text":"first page"}]}\n```\n\n'
        '```json\n{"answers":[{"question_number":"Q1","extracted_text":"second page"},'
        '{"question_number":"Question 2","extracted_text":"answer two"}]}\n```'
    )

    result = ocr_engine.parse_vlm_json_output(text)

    assert set(result.keys()) == {'Q1', 'Q2'}
    assert 'first page' in result['Q1']
    assert 'second page' in result['Q1']
    assert result['Q2'] == 'answer two'


def test_parse_vlm_json_output_falls_back_to_regex():
    """Invalid JSON should use the legacy regex splitter as a fallback"""
    text = "Q1:\nPhotosynthesis answer\nQ2:\nNewton answer"

    result = ocr_engine.parse_vlm_json_output(text)

    assert set(result.keys()) == {'Q1', 'Q2'}
    assert 'Photosynthesis' in result['Q1']
    assert 'Newton' in result['Q2']


def test_extract_unified_text_keeps_numbered_subpoints_in_one_answer():
    """Numbered sub-points must stay inside the single unified answer string."""
    import json

    answer = (
        "Vaccines train the immune system.\n"
        "1. mRNA Vaccines\n"
        "2. Viral Vector Vaccines\n"
        "3. Memory cell formation"
    )
    payload = json.dumps({'student_answer': answer})

    unified = ocr_engine.extract_unified_text(payload)

    assert unified == answer
    assert '1. mRNA Vaccines' in unified
    assert '3. Memory cell formation' in unified
    assert set(ocr_engine.parse_vlm_json_output(payload).keys()) == {'Q1'}


def test_extract_unified_text_reunifies_legacy_multi_question_output():
    """A legacy Q1/Q2/Q3 response is folded back into one continuous document string."""
    import json

    payload = json.dumps({
        'answers': [
            {'question_number': 'Q1', 'extracted_text': '1. mRNA Vaccines'},
            {'question_number': 'Q2', 'extracted_text': '2. Viral Vector Vaccines'},
            {'question_number': 'Q3', 'extracted_text': '3. Memory cell formation'},
        ]
    })

    unified = ocr_engine.extract_unified_text(payload)

    assert 'mRNA Vaccines' in unified
    assert 'Viral Vector Vaccines' in unified
    assert 'Memory cell formation' in unified
    assert 'Q2' not in unified
    assert 'Q3' not in unified
