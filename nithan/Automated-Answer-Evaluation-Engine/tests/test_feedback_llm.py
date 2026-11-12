import json
import logging
from types import SimpleNamespace

import groq

from src import feedback_llm


def _groq_completion(text):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


def test_generate_feedback_uses_groq_primary(monkeypatch, caplog):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _groq_completion("Groq explains the score. Groq suggests improvement.")

    class FakeGroq:
        def __init__(self, api_key):
            captured['api_key'] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('MODEL_NAME', 'test-model')
    monkeypatch.setattr(groq, 'Groq', FakeGroq)
    monkeypatch.setattr(
        feedback_llm,
        '_call_ollama',
        lambda prompt: (_ for _ in ()).throw(AssertionError('Ollama should not be called')),
    )

    with caplog.at_level(logging.INFO):
        feedback = feedback_llm.generate_feedback(
            student_score=0.8,
            reference_answer='Reference answer',
            student_answer='Student answer',
        )

    assert 'Groq explains the score' in feedback
    assert captured['api_key'] == 'test-key'
    assert captured['model'] == 'test-model'
    assert feedback_llm.LAST_INFERENCE_MODE == 'Groq API (test-model)'
    assert 'Inference Mode: Groq API (test-model)' in caplog.text


def test_generate_feedback_falls_back_to_ollama_when_groq_missing(monkeypatch, caplog):
    monkeypatch.delenv('GROQ_API_KEY', raising=False)
    monkeypatch.setenv('MODEL_NAME', 'test-model')
    monkeypatch.setattr(
        feedback_llm,
        '_call_ollama',
        lambda prompt: 'Ollama explains the score. Ollama suggests improvement.',
    )

    with caplog.at_level(logging.INFO):
        feedback = feedback_llm.generate_feedback(
            student_score=None,
            student_answer='An answer',
            has_reference=False,
            scoring_mode='zero_shot_llm',
            max_marks=10.0,
        )

    assert 'Ollama explains the score' in feedback
    assert feedback_llm.LAST_INFERENCE_MODE == 'Local Ollama Fallback'
    assert 'Inference Mode: Local Ollama Fallback' in caplog.text


def test_generate_feedback_falls_back_when_groq_raises(monkeypatch, caplog):
    class FailingGroq:
        def __init__(self, api_key):
            self.chat = SimpleNamespace(completions=self)

        def create(self, **kwargs):
            raise RuntimeError('rate limited')

    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('MODEL_NAME', 'test-model')
    monkeypatch.setattr(groq, 'Groq', FailingGroq)
    monkeypatch.setattr(
        feedback_llm,
        '_call_ollama',
        lambda prompt: 'Fallback explains the score. Fallback suggests improvement.',
    )

    with caplog.at_level(logging.INFO):
        feedback = feedback_llm.generate_feedback(
            student_score=0.5,
            reference_answer='Reference',
            student_answer='Student',
        )

    assert 'Fallback explains the score' in feedback
    assert feedback_llm.LAST_INFERENCE_MODE == 'Local Ollama Fallback'
    assert 'Inference Mode: Local Ollama Fallback' in caplog.text


def test_zero_shot_groq_returns_json_marks_and_complete_feedback(monkeypatch):
    captured = {}
    payload = {
        'estimated_marks': 8.5,
        'max_marks': 10.0,
        'qualitative_feedback': (
            "The student provides a comprehensive 8-point explanation of Earth's "
            "sphericity along with an accurate Geoid vs. Spheroid diagram. "
            "To improve, discuss gravity anomalies or Eratosthenes' calculation."
        ),
    }

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return _groq_completion(json.dumps(payload))

    class FakeGroq:
        def __init__(self, api_key):
            captured['api_key'] = api_key
            self.chat = SimpleNamespace(completions=FakeCompletions())

    monkeypatch.setenv('GROQ_API_KEY', 'test-key')
    monkeypatch.setenv('MODEL_NAME', 'test-model')
    monkeypatch.setattr(groq, 'Groq', FakeGroq)

    result = feedback_llm.generate_feedback_result(
        student_score=None,
        student_answer='Earth is an oblate spheroid with a geoid diagram.',
        has_reference=False,
        scoring_mode='zero_shot_llm',
        question_text='What do you mean by Geoid? Discuss evidence of Earth sphericity.',
        max_marks=10.0,
    )

    assert result['estimated_marks'] == 8.5
    assert result['max_marks'] == 10.0
    assert result['parsed_json'] is True
    assert result['qualitative_feedback'] == payload['qualitative_feedback']
    assert 'Geoid vs. Spheroid diagram' in result['qualitative_feedback']
    assert result['qualitative_feedback'].endswith("Eratosthenes' calculation.")
    assert captured['response_format'] == {'type': 'json_object'}
    assert captured['max_tokens'] >= 500
    system_prompt = captured['messages'][0]['content']
    assert 'JSON' in system_prompt
    assert 'exactly two complete sentences' in system_prompt
    user_prompt = captured['messages'][1]['content']
    assert '"estimated_marks"' in user_prompt
    assert '"qualitative_feedback"' in user_prompt


def test_zero_shot_fenced_json_is_parsed_without_truncating_abbreviation():
    raw = (
        '```json\n'
        '{"estimated_marks": "8.5", "max_marks": 10, "qualitative_feedback": '
        '"The answer explains the geoid using a geoid vs. spheroid diagram. '
        'To improve, mention gravity anomalies."}\n'
        '```'
    )

    parsed = feedback_llm._parse_zero_shot_response(raw, 10.0, [])

    assert parsed['estimated_marks'] == 8.5
    assert parsed['parsed_json'] is True
    assert parsed['qualitative_feedback'] == (
        'The answer explains the geoid using a geoid vs. spheroid diagram. '
        'To improve, mention gravity anomalies.'
    )


def test_truncated_zero_shot_json_salvages_feedback_and_marks():
    raw = (
        '{"estimated_marks": 7.5, "max_marks": 10.0, '
        '"qualitative_feedback": "The answer includes the geoid and a labelled '
        'diagram. To improve, add the Bedford level experiment.'
    )

    parsed = feedback_llm._parse_zero_shot_response(raw, 10.0, [])

    assert parsed['estimated_marks'] == 7.5
    assert parsed['parsed_json'] is False
    assert parsed['qualitative_feedback'] == (
        'The answer includes the geoid and a labelled diagram. '
        'To improve, add the Bedford level experiment.'
    )
