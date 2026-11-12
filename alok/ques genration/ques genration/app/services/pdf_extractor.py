import re
from pathlib import Path
import pdfplumber

class DocumentExtractor:
    @staticmethod
    def extract_text_from_file(file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".pdf":
            return DocumentExtractor._extract_from_pdf(path)
        elif path.suffix.lower() in [".txt", ".md"]:
            with open(path, "r", encoding="utf-8") as f:
                return DocumentExtractor._clean_text(f.read())
        else:
            raise ValueError(f"Unsupported file format: {path.suffix}. Use PDF or TXT.")

    @staticmethod
    def _extract_from_pdf(path: Path) -> str:
        extracted_pages = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    extracted_pages.append(text)
        
        full_text = "\n\n".join(extracted_pages)
        return DocumentExtractor._clean_text(full_text)

    @staticmethod
    def _clean_text(text: str) -> str:
        # Remove repetitive header/footer artifacts like 'Page 1 of 5'
        text = re.sub(r'Page\s+\d+\s+of\s+\d+', '', text, flags=re.IGNORECASE)
        # Normalize multiple spaces & excessive newlines
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()