import csv
import os
import tempfile

from PIL import Image
from src import pdf_processor, ocr_engine, rubric_evaluator, feedback_llm


def test_end_to_end_pipeline_with_csv():
    """End-to-end integration test using CSV datasets"""
    # Create a temporary CSV with test data
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, newline='') as tmp_csv:
        writer = csv.writer(tmp_csv)
        writer.writerow(['question', 'student_answer', 'reference_answer'])
        writer.writerow(['What is photosynthesis?', 
                        'Plants use sunlight to make food from carbon dioxide and water',
                        'Photosynthesis is the process by which plants use sunlight, water, and carbon dioxide to create oxygen and energy in the form of sugar'])
        writer.writerow(['Capital of France?', 
                        'Paris is the capital',
                        'Paris is the capital and largest city of France'])
        csv_path = tmp_csv.name
    
    try:
        # Read CSV
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        assert len(rows) > 0
        
        for row in rows:
            student_answer = row['student_answer']
            reference_answer = row['reference_answer']
            
            # Evaluate using rubric
            eval_result = rubric_evaluator.evaluate_answer(student_answer, reference_answer)
            assert isinstance(eval_result, dict)
            assert 'score' in eval_result or 'combined_score' in eval_result
            
            score = eval_result.get('score', eval_result.get('combined_score', 0))
            
            # Get missing keywords
            missing = []
            student_words = set(student_answer.lower().split())
            ref_words = set(reference_answer.lower().split())
            # Find important missing words (longer than 3 chars)
            for w in ref_words:
                if len(w) > 3 and w not in student_words:
                    missing.append(w)
            
            # Generate feedback
            feedback = feedback_llm.generate_feedback(score, missing, reference_answer, student_answer)
            assert isinstance(feedback, str)
            assert len(feedback) > 0
            # Should be 2 sentences
            sentence_count = feedback.count('.') + feedback.count('!') + feedback.count('?')
            assert sentence_count >= 1  # At least has sentences
            
    finally:
        os.unlink(csv_path)


def test_zero_shot_feedback_without_reference():
    """Feedback generation should accept the zero-shot fallback flag without a reference"""
    feedback = feedback_llm.generate_feedback(
        student_score=None,
        student_answer="Plants use sunlight to make food.",
        awarded_marks=None,
        max_marks=5.0,
        has_reference=False,
        scoring_mode="zero_shot_llm",
    )
    assert isinstance(feedback, str)
    assert len(feedback) > 0
