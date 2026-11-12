import csv

import pandas as pd

from src import data_loader


def _write_paper(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Q. no', 'Question', 'Marks', 'reference_answer', 'keywords'])
        writer.writerows(rows)


def _build_dataset(base_dir):
    _write_paper(
        base_dir / 'Class 6' / 'biology' / 'paper_1.csv',
        [
            ['1', 'What is a cell?', '10', 'A cell is the basic unit.', 'cell,unit'],
            ['2', 'What is DNA?', '5', '', ''],
        ],
    )
    _write_paper(
        base_dir / 'Class 6' / 'biology' / 'paper_2.csv',
        [['1', 'What is photosynthesis?', '5', '', '']],
    )
    _write_paper(
        base_dir / 'Class 6' / 'economics' / 'paper_1.csv',
        [['1', 'What is GDP?', '10', '', '']],
    )
    _write_paper(
        base_dir / 'Class 7' / 'polity' / 'paper_1.csv',
        [['1', 'What is a constitution?', '10', '', '']],
    )
    # Empty subject folder must not be advertised as available.
    (base_dir / 'Class 6' / 'empty_subject').mkdir(parents=True)
    # Legacy flat subject folder should not appear as a class.
    _write_paper(
        base_dir / 'ECONOMICS' / 'paper_1.csv',
        [['1', 'Legacy question', '5', '', '']],
    )


def test_dynamic_class_subject_paper_scanners(tmp_path):
    _build_dataset(tmp_path)

    assert data_loader.get_available_classes(tmp_path) == ['Class 6', 'Class 7']
    assert data_loader.get_available_subjects('Class 6', tmp_path) == [
        'biology',
        'economics',
    ]
    assert data_loader.get_available_papers('Class 6', 'biology', tmp_path) == [
        'paper_1',
        'paper_2',
    ]


def test_load_paper_csv_returns_canonical_dataframe(tmp_path):
    _build_dataset(tmp_path)

    frame = data_loader.load_paper_csv(
        'Class 6',
        'biology',
        'paper_1',
        base_dir=tmp_path,
    )

    assert isinstance(frame, pd.DataFrame)
    assert list(frame.columns) == list(data_loader.CANONICAL_COLUMNS)
    assert len(frame) == 2
    assert frame.iloc[0]['question_text'] == 'What is a cell?'
    assert frame.iloc[0]['max_marks'] == 10


def test_get_question_options_uses_new_hierarchy(tmp_path):
    _build_dataset(tmp_path)

    options = data_loader.get_question_options(
        'Class 6',
        'biology',
        'paper_1',
        base_dir=tmp_path,
    )

    assert options[0] == 'All Questions'
    assert options[1].startswith('Q1: What is a cell?')
    assert options[2].startswith('Q2: What is DNA?')


def test_sample_data_exposes_class_6_and_new_layout():
    classes = data_loader.get_available_classes()
    assert 'Class 6' in classes

    subjects = data_loader.get_available_subjects('Class 6')
    assert 'Science' in subjects

    papers = data_loader.get_available_papers('Class 6', 'Science')
    assert 'paper_1' in papers
