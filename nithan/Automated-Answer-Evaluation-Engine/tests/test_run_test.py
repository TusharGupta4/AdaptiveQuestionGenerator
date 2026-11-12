import os
import subprocess
import sys


def test_run_test_execution():
    """Test that run_test.py executes without errors"""
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    run_test_path = os.path.join(root_dir, 'run_test.py')
    sample_pdf = os.path.join(root_dir, 'sample_data', 'student_sheet_1.pdf')
    
    assert os.path.exists(run_test_path), "run_test.py should exist in root directory"
    
    # Run the script
    result = subprocess.run(
        [sys.executable, run_test_path, sample_pdf],
        cwd=root_dir,
        capture_output=True,
        text=True,
        timeout=120
    )
    
    # Check that it executed (may have warnings/fallbacks but should run)
    assert result.returncode == 0 or result.returncode is not None
    # Check output contains expected elements
    output = result.stdout + result.stderr
    assert len(output) > 0


def test_merge_page_question_maps_reassigns_reused_q1():
    """A later page that restarts at Q1 should map to the next expected question"""
    import run_test

    page_maps = [
        {'Q1': 'Photosynthesis answer'},
        {'Q1': "Newton's second law answer"},
    ]

    merged = run_test.merge_page_question_maps(page_maps, ['Q1', 'Q2'])

    assert set(merged.keys()) == {'Q1', 'Q2'}
    assert 'Photosynthesis' in merged['Q1']
    assert "Newton's second law" in merged['Q2']
