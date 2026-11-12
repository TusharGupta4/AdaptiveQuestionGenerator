"""
STEP 2 : raw text -> cleaned text
--------------------------------
- Removes blank lines
- Strips stray non-printable control characters that PyMuPDF sometimes
  leaves behind (these were causing junk like "Question 1\x08" earlier,
  which broke the parser in step 3)
- Keeps "--- Page N ---" markers untouched (needed by step 3 & 4)
"""

from pathlib import Path

project_folder = Path(__file__).parent.parent
input_folder = project_folder / "extracted_text"
output_folder = project_folder / "cleaned_questions"
output_folder.mkdir(exist_ok=True)

text_files = sorted(input_folder.glob("*.txt"))


def strip_control_chars(line: str) -> str:
    return "".join(ch for ch in line if ch == "\t" or ord(ch) >= 32)


for input_path in text_files:
    text = input_path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    cleaned_lines = []
    for line in text.splitlines():
        line = strip_control_chars(line).strip()
        if line:
            cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)

    output_name = input_path.stem + "_cleaned.txt"
    output_path = output_folder / output_name
    output_path.write_text(cleaned_text, encoding="utf-8")

    print(f"Cleaned: {input_path.name} -> {output_name}")

print("Cleaning completed.")
