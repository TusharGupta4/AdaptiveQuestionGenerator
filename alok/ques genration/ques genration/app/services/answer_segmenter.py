import re
from typing import Dict

class AnswerSegmenter:
    @staticmethod
    def segment_answers(raw_text: str) -> Dict[int, str]:
        """
        Splits raw OCR answer sheet into a dictionary mapping:
        { question_number: student_answer_text }
        """
        # Regex matching variants like:
        # "Ans 1:", "Answer 1.", "Q1.", "Q. 1", "Question 1:", "1." at beginning of line
        pattern = r'(?:^|\n)(?:Ans(?:wer)?\.?|Q(?:uestion)?\.?|\b)\s*(\d+)[\s.:\)\-]+'
        
        splits = re.split(pattern, raw_text, flags=re.IGNORECASE)
        segmented_answers: Dict[int, str] = {}

        if len(splits) > 1:
            i = 1
            while i < len(splits):
                try:
                    q_num = int(splits[i].strip())
                    answer_body = splits[i+1].strip() if (i+1) < len(splits) else ""
                    # Clean redundant headers inside the body
                    answer_body = re.sub(r'^(?:Ans(?:wer)?|Solution)[\s.:\-]+', '', answer_body, flags=re.IGNORECASE).strip()
                    
                    if answer_body:
                        segmented_answers[q_num] = answer_body
                except (ValueError, IndexError):
                    pass
                i += 2
        else:
            # Fallback: if no clear headers found, assign entire text to Q1
            segmented_answers[1] = raw_text.strip()

        return segmented_answers