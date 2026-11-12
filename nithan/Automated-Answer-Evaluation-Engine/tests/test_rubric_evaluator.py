from src import rubric_evaluator


def test_cosine_similarity():
    """Test cosine similarity calculation"""
    vec1 = [1.0, 0.0, 0.0]
    vec2 = [1.0, 0.0, 0.0]
    sim = rubric_evaluator.cosine_similarity(vec1, vec2)
    assert isinstance(sim, float)
    assert abs(sim - 1.0) < 0.001
    
    vec3 = [1.0, 0.0, 0.0]
    vec4 = [0.0, 1.0, 0.0]
    sim2 = rubric_evaluator.cosine_similarity(vec3, vec4)
    assert abs(sim2 - 0.0) < 0.001


def test_keyword_match_ratio():
    """Test keyword match ratio calculation"""
    student = "Photosynthesis uses sunlight to convert carbon dioxide and water into glucose"
    reference = "Photosynthesis uses sunlight, carbon dioxide and water to produce glucose and oxygen"
    ratio = rubric_evaluator.keyword_match_ratio(student, reference)
    assert isinstance(ratio, float)
    assert 0.0 <= ratio <= 1.0
    assert ratio > 0.0  # Should have some matches


def test_evaluate_answer_combined_score():
    """Test that evaluate_answer combines embeddings and keyword matching"""
    student = "The capital of France is Paris"
    reference = "Paris is the capital city of France"
    result = rubric_evaluator.evaluate_answer(student, reference)
    
    assert isinstance(result, dict)
    # Check for score
    assert any(k in result for k in ['score', 'combined_score', 'total_score'])
    score = result.get('score', result.get('combined_score', result.get('total_score')))
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0
    # Check components are present
    assert any(k in result for k in ['embedding_similarity', 'semantic_similarity'])
    assert any(k in result for k in ['keyword_match_ratio', 'keyword_ratio', 'keyword_score'])


def test_fuzzy_keyword_matching_with_typos():
    """Test that minor OCR spelling typos match reference keywords with fuzzy matching"""
    # Test with typos: Glucose as Glueese, Photosynthesis as Photosynthesic
    student = "Photosynthesic uses sunlight to convert carbon dioxide and water into Glueese"
    reference = "Photosynthesis uses sunlight, carbon dioxide and water to produce glucose and oxygen"
    ratio = rubric_evaluator.keyword_match_ratio(student, reference)
    assert isinstance(ratio, float)
    assert 0.0 <= ratio <= 1.0
    # With fuzzy matching (>=75% similarity), typos should match
    assert ratio >= 0.4  # Should catch at least some of the misspelled keywords
    
    # Direct test of fuzzy match
    assert rubric_evaluator.fuzzy_match_keyword('glucose', 'Glueese', threshold=0.75) or \
           rubric_evaluator.fuzzy_match_keyword('Glucose', 'Glueese', threshold=0.75)
    assert rubric_evaluator.fuzzy_match_keyword('Photosynthesis', 'Photosynthesic', threshold=0.75)


def test_evaluate_question_uses_only_selected_question_reference(monkeypatch):
    """The question record's own reference/keywords must be passed to the evaluator."""
    captured = {}

    def fake_evaluate(student_text, reference_answer, **kwargs):
        captured['student_text'] = student_text
        captured['reference_answer'] = reference_answer
        captured['keywords'] = kwargs.get('keywords')
        captured['max_marks'] = kwargs.get('max_marks')
        return {'has_reference': True, 'max_marks': kwargs.get('max_marks')}

    monkeypatch.setattr(rubric_evaluator, 'evaluate_answer', fake_evaluate)

    result = rubric_evaluator.evaluate_question(
        'student vaccine answer',
        {
            'question_id': 'Q1',
            'question_text': 'Vaccine development',
            'reference_ans': 'vaccine reference key',
            'key_words': 'vaccine,memory cells',
            'max_marks': '10.0',
        },
    )

    assert captured['student_text'] == 'student vaccine answer'
    assert captured['reference_answer'] == 'vaccine reference key'
    assert captured['keywords'] == 'vaccine,memory cells'
    assert captured['max_marks'] == 10.0
    assert result['question_id'] == 'Q1'
    assert result['question_text'] == 'Vaccine development'


def test_subject_weight_matrix_and_equation_priority(monkeypatch):
    """STEM weights prioritise equation accuracy while humanities stay unchanged."""
    monkeypatch.setattr(
        rubric_evaluator,
        'get_embeddings',
        lambda texts: [[1.0, 0.0] for _ in texts],
    )

    humanities = rubric_evaluator.get_subject_weights(subject_type='humanities')
    assert humanities['semantic'] == 0.40
    assert 'equation_accuracy' not in humanities

    stem = rubric_evaluator.get_subject_weights(subject_type='stem')
    assert stem['equation_accuracy'] > stem['semantic']

    result = rubric_evaluator.evaluate_answer(
        "The relation is $F = m a$.",
        "Newton's second law is $F = m \\cdot a$.",
        keywords='force,mass,acceleration',
        subject_type='stem',
    )
    assert result['subject_type'] == 'stem'
    assert result['equation_score'] > 0
    assert result['sub_scores']['equation_accuracy'] == result['equation_score']
    assert result['weights_used']['equation_accuracy'] > 0


def test_diagram_based_labels_match_against_required_csv_labels(monkeypatch):
    """Diagram papers score extracted visual labels against required labels."""
    monkeypatch.setattr(
        rubric_evaluator,
        'get_embeddings',
        lambda texts: [[1.0, 0.0] for _ in texts],
    )

    result = rubric_evaluator.evaluate_answer(
        "The diagram shows sunlight and water entering the leaf.",
        "Photosynthesis uses sunlight and water.",
        keywords='photosynthesis,sunlight,water',
        subject_type='diagram_based',
        required_diagram_labels='Sunlight, Water, Chlorophyll',
        diagrams=[{
            'figure_id': 'Fig 1',
            'labels': ['Sunlight', 'Water', 'Leaf'],
            'spatial_arrangement': 'top to bottom',
        }],
    )

    assert result['subject_type'] == 'diagram_based'
    assert result['diagram_label_score'] == (2 / 3) * 100
    assert result['diagram_labels_missing'] == ['Chlorophyll']
    assert result['weights_used']['diagram_label'] > result['weights_used']['semantic']


def test_evaluate_answer_missing_reference_uses_zero_shot(monkeypatch):
    """Missing reference data should skip embeddings/keywords and defer to zero-shot LLM"""
    def fail_embeddings(*args, **kwargs):
        raise AssertionError("Embeddings must not be computed without a reference")

    monkeypatch.setattr(rubric_evaluator, 'get_embeddings', fail_embeddings)

    result = rubric_evaluator.evaluate_answer(
        "An answer without a reference key.",
        "",
        keywords="",
        max_marks=10.0,
    )

    assert result['has_reference'] is False
    assert result['scoring_mode'] == 'zero_shot_llm'
    assert result['awarded_marks'] is None
    assert result['marks_awarded'] is None
    assert result['max_marks'] == 5.0
    assert result['semantic_score'] is None
    assert result['fuzzy_keyword_score'] is None
    assert 'word_count' in result
    assert 'ocr_quality_score' in result
