#!/usr/bin/env python3
import argparse
import csv
import os
import sys
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src import pdf_processor, ocr_engine, rubric_evaluator, feedback_llm


def load_questions_csv(csv_path: str) -> Dict:
    questions = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                qid = row.get('question_id', row.get('id', ''))
                questions[qid] = {
                    'reference_ans': row.get('reference_ans', row.get('answer', row.get('reference_answer', ''))),
                    'key_words': row.get('key_words', row.get('keywords', '')),
                    'max_marks': float(row.get('max_marks', row.get('marks', 5.0)))
                }
    except Exception as e:
        print(f"Warning: Could not load {csv_path}: {e}")
    return questions


def load_model_answers_csv(csv_path: str) -> Dict:
    model_answers = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                qid = row.get('question_id', row.get('id', ''))
                model_answers[qid] = {
                    'question_text': row.get('question_text', row.get('question', '')),
                    'max_marks': float(row.get('max_marks', row.get('marks', 5.0)))
                }
    except Exception as e:
        print(f"Warning: Could not load {csv_path}: {e}")
    return model_answers


def merge_page_question_maps(page_maps, expected_ids):
    """Merge per-page structured results, reassigning reused page-local IDs to missing expected questions."""
    merged = {}
    for page_map in page_maps:
        if not page_map:
            continue
        for qid, block in page_map.items():
            target = qid
            if target in merged:
                missing_ids = [expected for expected in expected_ids if expected not in merged]
                if len(page_map) == 1 and missing_ids:
                    target = missing_ids[0]
                else:
                    merged[target] = f"{merged[target].rstrip()}\n{block.lstrip()}"
                    continue
            if target in merged:
                merged[target] = f"{merged[target].rstrip()}\n{block.lstrip()}"
            else:
                merged[target] = block
    return merged


def main():
    parser = argparse.ArgumentParser(description='Process student answer sheets - Full Pipeline')
    parser.add_argument('file_path', nargs='?', default='sample_data/student_sheet_1.pdf',
                        help='Path to image or PDF file')
    args = parser.parse_args()
    
    file_path = args.file_path
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 70)
    print("STUDENT ANSWER SHEET PROCESSING - FULL PIPELINE")
    print("=" * 70)
    print(f"File: {file_path}")
    print()
    
    # Load CSV data
    questions_csv = os.path.join(root_dir, 'sample_data', 'questions.csv')
    model_csv = os.path.join(root_dir, 'sample_data', 'model_answers.csv')
    if not os.path.exists(questions_csv):
        questions_csv = 'sample_data/questions.csv'
    if not os.path.exists(model_csv):
        model_csv = 'sample_data/model_answers.csv'
    
    questions_data = load_questions_csv(questions_csv)
    model_answers_data = load_model_answers_csv(model_csv)
    print(f"Loaded {len(questions_data)} questions from CSV")
    print()
    
    # Process file
    try:
        print("Processing file into high-DPI images (300 DPI)...")
        images = pdf_processor.process_file(file_path, dpi=300)
        print(f"✓ Converted to {len(images)} high-DPI image(s)")
        print()
    except Exception as e:
        print(f"Error processing file: {e}")
        return
    
    all_text = []
    page_results = []
    
    print("=" * 70)
    print("OCR PROCESSING")
    print("=" * 70)
    
    for i, img in enumerate(images):
        print(f"\n--- Page {i+1} ---")
        result = ocr_engine.extract_text_with_confidence(
            img,
            page_number=i + 1,
            total_pages=len(images),
        )
        raw_text = result.get('text', result.get('full_text', ''))
        text = ocr_engine.extract_unified_text(raw_text)
        all_text.append(text)
        page_results.append({'page_num': i+1, 'text': text, 'result': result})
        
        engine = result.get('engine', result.get('method', 'Unknown'))
        print(f"Active OCR Engine: {engine}")
        conf = result.get('average_confidence', result.get('confidence', 0))
        print(f"OCR Quality - Average Confidence: {conf:.2f}%")
        print()
    
    combined_text = ocr_engine.assemble_page_texts(all_text)
    
    print("=" * 70)
    print("PAGE-BY-PAGE EXTRACTED TEXT")
    print("=" * 70)
    for pr in page_results:
        print(f"\n--- Page {pr['page_num']} Raw OCR Text ---")
        print("-" * 70)
        print(pr['text'])
        print("-" * 70)
    print()
    
    # Structured VLM parsing with regex fallback for non-JSON OCR output
    print("=" * 70)
    print("STRUCTURED VLM QUESTION PARSING")
    print("=" * 70)
    expected_question_ids = list(dict.fromkeys(
        list(questions_data.keys()) + list(model_answers_data.keys())
    ))
    print("Parsing questions across the FULL assembled document...")
    question_map = ocr_engine.extract_full_document_questions(
        combined_text,
        expected_question_ids,
    )
    if not question_map:
        question_map = ocr_engine.parse_vlm_json_output(combined_text)
    
    if not question_map:
        print("\n⚠️  FALLBACK WARNING: Question blocks missing!")
        print("No structured question blocks found (Q1:, 1), etc.)")
        print("Please run the Streamlit UI for manual tagging.")
        print()
    else:
        print(f"✓ Parsed into {len(question_map)} structured question block(s):")
        for qid, block in question_map.items():
            preview = block[:100].replace('\n', ' ')
            print(f"  - {qid}: {preview}...")
    print()
    
    # Evaluation
    print("=" * 70)
    print("SUB-SCORE METRICS & EVALUATION")
    print("=" * 70)
    
    evaluated_any = False
    question_ids = list(dict.fromkeys(list(questions_data.keys()) + list(question_map.keys())))
    for qid in question_ids:
        qdata = questions_data.get(qid, {})
        reference = qdata.get('reference_ans', '') or ''
        keywords = qdata.get('key_words', '') or ''
        max_marks = qdata.get('max_marks', model_answers_data.get(qid, {}).get('max_marks', 5.0))
        if max_marks is None:
            max_marks = 5.0
        question_text = model_answers_data.get(qid, {}).get('question_text', '')
        
        # Use question map if available, else combined text
        student_text = question_map.get(qid, combined_text) if question_map else combined_text
        
        eval_result = rubric_evaluator.evaluate_answer(
            student_text, reference, 
            keywords=keywords,
            max_marks=max_marks,
            min_words=10
        )
        
        has_reference = eval_result.get('has_reference', True)
        scoring_mode = eval_result.get('scoring_mode', 'rubric')
        
        print(f"\n{'='*60}")
        print(f"Question: {qid}")
        print(f"{'='*60}")
        if has_reference:
            print(f"Scoring Mode: {scoring_mode}")
            print(f"Sub-Score Breakdown:")
            print(f"  a) Semantic Similarity (40%): {eval_result['semantic_score']:.2f}%")
            print(f"  b) Fuzzy Keyword Coverage (30%): {eval_result['fuzzy_keyword_score']:.2f}% [threshold >= 65%]")
            print(f"  c) Word Count Penalty (15%): {eval_result['word_count_score']:.2f}% (words: {eval_result['word_count']}, penalty: {eval_result['word_count_penalty_applied']})")
            print(f"  d) OCR Quality Penalty (15%): {eval_result['ocr_quality_score']:.2f}% (garbled: {eval_result['garbled_ratio']:.2%}, penalty: {eval_result['ocr_penalty_applied']})")
            print(f"\n  Marks Awarded: {eval_result['awarded_marks']:.2f} / {eval_result['max_marks']}")
        else:
            print(f"Scoring Mode: {scoring_mode} (no reference answer key found)")
            print("Sub-Score Breakdown:")
            print("  a) Semantic Similarity: skipped (no reference answer)")
            print("  b) Fuzzy Keyword Coverage: skipped (no reference keywords)")
            print(f"  c) Word Count Penalty (15%): {eval_result['word_count_score']:.2f}% (words: {eval_result['word_count']}, penalty: {eval_result['word_count_penalty_applied']})")
            print(f"  d) OCR Quality Penalty (15%): {eval_result['ocr_quality_score']:.2f}% (garbled: {eval_result['garbled_ratio']:.2%}, penalty: {eval_result['ocr_penalty_applied']})")
            print(f"\n  Marks Awarded: pending zero-shot LLM estimate (max {eval_result['max_marks']:.2f})")
        
        # Missing keywords
        missing_keywords = []
        if has_reference and keywords:
            kw_list = [k.strip() for k in keywords.split(',')]
            student_lower = student_text.lower()
            for kw in kw_list:
                if kw and kw.lower() not in student_lower and not rubric_evaluator.fuzzy_match_keyword(kw, student_text, 65.0):
                    missing_keywords.append(kw)
        print(f"  Missing Keywords: {', '.join(missing_keywords) if missing_keywords else 'None'}")
        
        # LLM Feedback
        print(f"\n  Qualitative LLM Feedback (Ollama):")
        try:
            recognized = []
            if has_reference and keywords:
                recognized = [k.strip() for k in keywords.split(',') if k.strip() and k.strip().lower() in student_text.lower()][:3]
            feedback = feedback_llm.generate_feedback(
                student_score=eval_result.get('score'),
                missing_keywords=missing_keywords,
                reference_answer=reference,
                student_answer=student_text,
                awarded_marks=eval_result.get('awarded_marks'),
                max_marks=eval_result.get('max_marks', max_marks),
                recognized_concepts=recognized,
                has_reference=has_reference,
                scoring_mode=scoring_mode,
                question_text=question_text
            )
            print(f"    {feedback}")
        except Exception as e:
            print(f"    Error: {e}")
        
        evaluated_any = True
    
    if not evaluated_any:
        print("\nNo questions evaluated. Check CSV files or question tagging.")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()
