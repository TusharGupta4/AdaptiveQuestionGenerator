import pytest

from src import config, feedback_llm, rubric_evaluator


def test_grade_profile_resolution():
    assert config.resolve_grade_profile('Class 6')['key'] == 'junior'
    assert config.resolve_grade_profile('Class 8')['key'] == 'junior'
    assert config.resolve_grade_profile('Class 9')['key'] == 'secondary'
    assert config.resolve_grade_profile('Class 10')['key'] == 'secondary'
    assert config.resolve_grade_profile('Class 11')['key'] == 'senior'
    assert config.resolve_grade_profile('Class 12')['key'] == 'senior'
    assert config.resolve_grade_profile(None) is None

    assert config.resolve_grade_profile('Class 6')['keyword_threshold'] == 45.0
    assert config.resolve_grade_profile('Class 9')['keyword_threshold'] == 60.0
    assert config.resolve_grade_profile('Class 12')['keyword_threshold'] == 75.0
    assert config.resolve_grade_profile('Class 6')['word_count_tolerance'] == 0.40


def test_grade_profiles_adjust_weight_priorities():
    junior = rubric_evaluator.get_subject_weights(
        subject_type='humanities',
        selected_class='Class 6',
    )
    secondary = rubric_evaluator.get_subject_weights(
        subject_type='humanities',
        selected_class='Class 9',
    )
    senior = rubric_evaluator.get_subject_weights(
        subject_type='humanities',
        selected_class='Class 12',
    )

    assert junior['fuzzy_keyword'] > secondary['fuzzy_keyword']
    assert senior['semantic'] > junior['semantic']
    assert senior['word_count'] < junior['word_count']

    for selected_class in ('Class 6', 'Class 9', 'Class 12'):
        stem = rubric_evaluator.get_subject_weights(
            subject_type='stem',
            selected_class=selected_class,
        )
        assert stem['equation_accuracy'] > stem['semantic']


def test_junior_keyword_threshold_is_more_lenient_than_senior():
    student = 'Photosynthesic uses sunlight to make Glueese'
    reference = 'Photosynthesis uses sunlight to make glucose'

    junior = rubric_evaluator.keyword_match_ratio(
        student,
        reference,
        threshold=45.0,
        formal=False,
    )
    senior = rubric_evaluator.keyword_match_ratio(
        student,
        reference,
        threshold=75.0,
        formal=True,
    )

    assert junior > senior
    assert rubric_evaluator.fuzzy_match_keyword(
        'glucose',
        student,
        threshold=45.0,
    )
    assert not rubric_evaluator.fuzzy_match_keyword(
        'glucose',
        student,
        threshold=75.0,
        formal=True,
    )


def test_evaluate_answer_applies_grade_profile(monkeypatch):
    monkeypatch.setattr(
        rubric_evaluator,
        'get_embeddings',
        lambda texts: [[1.0, 0.0] for _ in texts],
    )

    student = 'Photosynthesic uses sunlight to make Glueese'
    reference = (
        'Photosynthesis uses sunlight, carbon dioxide and water to make glucose '
        'and oxygen.'
    )
    keywords = 'photosynthesis,sunlight,carbon dioxide,water,glucose,oxygen'

    junior = rubric_evaluator.evaluate_answer(
        student,
        reference,
        keywords=keywords,
        selected_class='Class 6',
        min_words=10,
    )
    senior = rubric_evaluator.evaluate_answer(
        student,
        reference,
        keywords=keywords,
        selected_class='Class 12',
        min_words=10,
    )

    assert junior['grade_profile'] == 'junior'
    assert senior['grade_profile'] == 'senior'
    assert junior['keyword_threshold'] == 45.0
    assert senior['keyword_threshold'] == 75.0
    assert junior['weights_used']['fuzzy_keyword'] > (
        senior['weights_used']['fuzzy_keyword']
    )
    assert junior['weights_used']['semantic'] < senior['weights_used']['semantic']
    assert junior['word_count_score'] > senior['word_count_score']
    assert junior['effective_min_words'] < senior['effective_min_words']
    assert senior['formal_term_validation'] is True


def test_evaluate_question_passes_selected_class(monkeypatch):
    captured = {}

    def fake_evaluate(student_text, reference_answer, **kwargs):
        captured.update(kwargs)
        return {'has_reference': True, 'max_marks': kwargs.get('max_marks')}

    monkeypatch.setattr(rubric_evaluator, 'evaluate_answer', fake_evaluate)

    result = rubric_evaluator.evaluate_question(
        'student response',
        {
            'question_no': 'Q1',
            'reference_answer': 'reference',
            'keywords': 'keyword',
            'max_marks': 5,
        },
        selected_class='Class 11',
    )

    assert captured['selected_class'] == 'Class 11'
    assert result['question_id'] == 'Q1'


def test_generate_feedback_passes_grade_persona_to_llm(monkeypatch):
    prompts = []

    def fake_groq(prompt, model_name, grade_profile=None):
        prompts.append((prompt, grade_profile))
        return 'The answer shows understanding. Add one more precise term.'

    monkeypatch.setattr(feedback_llm, '_call_groq', fake_groq)

    feedback_llm.generate_feedback(
        student_score=0.7,
        reference_answer='reference',
        student_answer='student',
        selected_class='Class 6',
    )
    feedback_llm.generate_feedback(
        student_score=0.7,
        reference_answer='reference',
        student_answer='student',
        selected_class='Class 12',
    )

    junior_prompt, junior_profile = prompts[0]
    senior_prompt, senior_profile = prompts[1]

    assert junior_profile['key'] == 'junior'
    assert senior_profile['key'] == 'senior'
    assert 'encouraging middle-school teacher' in junior_prompt
    assert 'strict senior examiner' in senior_prompt
    assert 'Class 6-8' in junior_prompt
    assert 'Class 11-12' in senior_prompt
    assert 'technical, formal, academic language' in senior_prompt.lower()
