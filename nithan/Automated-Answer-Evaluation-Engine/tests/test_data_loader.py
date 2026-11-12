import csv
from pathlib import Path

from src import data_loader

TRIAL_DIR = Path(data_loader.DEFAULT_SAMPLE_DIR) / 'test_data'


def test_economics_subject_and_zero_shot_questions():
    subjects = data_loader.get_subjects(TRIAL_DIR)
    assert 'ECONOMICS' in subjects
    assert 'paper_1' in data_loader.get_papers('economics', TRIAL_DIR)

    questions = data_loader.load_paper('ECONOMICS', 'PAPER_1', base_dir=TRIAL_DIR)
    assert len(questions) == 5

    first = questions[0]
    assert first['question_no'] == 'Q1'
    assert first['max_marks'] == 10.0
    assert first['reference_answer'] == ''
    assert first['keywords'] == ''
    assert first['scoring_mode'] == 'zero_shot_llm'
    assert first['has_reference'] is False
    assert 'Gross Domestic Product' in first['question_text']


def test_get_question_options_format():
    options = data_loader.get_question_options(
        'ECONOMICS',
        'paper_1',
        base_dir=TRIAL_DIR,
    )

    assert options[0] == 'All Questions'
    assert options[1].startswith(
        'Q1: What do you understand by Gross Domestic Product'
    )
    assert len(options) == 6


def test_flexible_headers_and_missing_reference(tmp_path):
    subject_dir = tmp_path / 'biology'
    subject_dir.mkdir()
    paper_path = subject_dir / 'paper_2.csv'

    with open(paper_path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Q. no', 'Question', 'Marks', 'reference_answer', 'keywords'])
        writer.writerow(['1', 'What is a cell?', '10', 'A cell is the basic unit.', 'cell,unit'])
        writer.writerow(['2', 'What is DNA?', '5', '', ''])

    subjects = data_loader.get_subjects(tmp_path)
    assert subjects == ['biology']
    assert data_loader.get_papers('BIOLOGY', tmp_path) == ['paper_2']

    questions = data_loader.load_paper('biology', 'paper_2', tmp_path)
    assert questions[0]['question_no'] == 'Q1'
    assert questions[0]['question_text'] == 'What is a cell?'
    assert questions[0]['max_marks'] == 10.0
    assert questions[0]['scoring_mode'] == 'rubric'
    assert questions[1]['max_marks'] == 5.0
    assert questions[1]['scoring_mode'] == 'zero_shot_llm'

    direct = data_loader.load_questions_csv(paper_path)
    assert len(direct) == 2
    assert direct[0]['question_no'] == 'Q1'


def test_missing_optional_columns_force_zero_shot(tmp_path):
    subject_dir = tmp_path / 'ECONOMICS'
    subject_dir.mkdir()
    paper_path = subject_dir / 'paper_1.csv'

    with open(paper_path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['q_no', 'question', 'marks'])
        writer.writerow(['1', 'Explain GDP.', '10'])

    questions = data_loader.load_questions('ECONOMICS', 'paper_1', tmp_path)
    assert questions[0]['reference_answer'] == ''
    assert questions[0]['keywords'] == ''
    assert questions[0]['scoring_mode'] == 'zero_shot_llm'
    assert questions[0]['max_marks'] == 10.0
