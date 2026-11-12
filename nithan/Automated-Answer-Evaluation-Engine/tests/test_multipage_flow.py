from pathlib import Path

import app
from src import data_loader, document_parser, ocr_engine, rubric_evaluator

TRIAL_DIR = Path(data_loader.DEFAULT_SAMPLE_DIR) / 'test_data'


def _multi_page_text():
    pages = [
        "Q1. What is GDP?\nGDP is the total value of goods",
        "and services produced in a country in a year.\nIt is calculated by expenditure method.",
        "Q2. GDP is not an index of welfare.\nWelfare includes health and education.",
        "Q3. Explain inclusions/exclusions.\n(a) pensions are transfers",
        "Q3 continued: (b) old car sale is not included.",
        "Q4. GDP deflator.\nIt is nominal/real GDP.",
        "Q4 continued: CPI measures consumer prices.\nWPI measures wholesale prices.",
        "Q5. Value-added method.\nSum of value added by firms.",
        "Q5 continued: Income method sums factor incomes.",
        "Expenditure method sums final spending.",
        "Page eleven continuation of Q5.",
        "Page twelve continuation of Q5.",
        "Page thirteen end of Q5.",
    ]
    return pages


def test_parser_groups_answers_across_page_boundaries():
    pages = _multi_page_text()
    full_text = ocr_engine.assemble_page_texts(pages)

    blocks = document_parser.extract_question_blocks(full_text)

    assert set(blocks) == {'Q1', 'Q2', 'Q3', 'Q4', 'Q5'}
    assert 'calculated by expenditure method' in blocks['Q1']
    assert 'Q2. GDP' not in blocks['Q1']
    assert 'health and education' in blocks['Q2']
    assert 'CPI measures' in blocks['Q4']
    assert 'WPI measures' in blocks['Q4']
    assert 'Page thirteen end of Q5' in blocks['Q5']


def test_extract_document_from_pages_assembles_all_pages(monkeypatch):
    import json

    page_payloads = iter([
        json.dumps({'student_answer': 'page one answer'}),
        json.dumps({'student_answer': 'page two answer'}),
        json.dumps({'student_answer': 'page three answer'}),
    ])

    def fake_extract(image, **kwargs):
        return {'text': next(page_payloads), 'average_confidence': 90.0}

    monkeypatch.setattr(ocr_engine, 'extract_text_with_confidence', fake_extract)

    document = ocr_engine.extract_document_from_pages([object(), object(), object()])

    assert document['page_texts'] == [
        'page one answer',
        'page two answer',
        'page three answer',
    ]
    assert document['full_text'] == (
        'page one answer\n\npage two answer\n\npage three answer'
    )


def test_extract_full_document_questions_without_vlm():
    full_text = ocr_engine.assemble_page_texts(_multi_page_text())

    blocks = ocr_engine.extract_full_document_questions(
        full_text,
        ['Q1', 'Q2', 'Q3', 'Q4', 'Q5'],
        use_groq=False,
    )

    assert list(blocks) == ['Q1', 'Q2', 'Q3', 'Q4', 'Q5']
    assert 'expenditure method' in blocks['Q1']
    assert 'Page thirteen end of Q5' in blocks['Q5']


def test_missing_tag_does_not_steal_another_questions_exact_block():
    questions = data_loader.load_paper('ECONOMICS', 'paper_1', base_dir=TRIAL_DIR)
    blocks = {
        'Q1': 'Gross domestic product measures total output.',
        'Q3': 'Pensions, old car sale, interest on national debt.',
        'Q4': 'GDP deflator is nominal GDP divided by real GDP.',
        'Q5': 'Value added, income and expenditure methods estimate national income.',
    }

    matches = rubric_evaluator.match_questions_to_blocks(questions, blocks)

    assert matches['Q1']['source'] == 'tag'
    assert matches['Q4']['source'] == 'tag'
    assert matches['Q4']['text'].startswith('GDP deflator')
    assert matches['Q2']['source'] == 'zero_shot'


def test_all_questions_map_covers_every_csv_question():
    pages = _multi_page_text()
    full_text = ocr_engine.assemble_page_texts(pages)
    questions = data_loader.load_paper('ECONOMICS', 'paper_1', base_dir=TRIAL_DIR)
    expected_ids = [question['question_no'] for question in questions]
    blocks = ocr_engine.extract_full_document_questions(
        full_text,
        expected_ids,
        use_groq=False,
    )

    question_map = app.build_question_text_map(
        pages,
        questions,
        app.ALL_QUESTIONS,
        None,
        question_blocks=blocks,
    )

    assert list(question_map) == expected_ids
    assert 'expenditure method' in question_map['Q1']
    assert 'Page thirteen end of Q5' in question_map['Q5']
