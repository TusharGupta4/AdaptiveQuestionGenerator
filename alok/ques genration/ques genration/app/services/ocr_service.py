import os
from pathlib import Path
from PIL import Image
from app.services.pdf_extractor import DocumentExtractor

class OCRService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # If text file or markdown
        if path.suffix.lower() in [".txt", ".md"]:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

        # If PDF file
        elif path.suffix.lower() == ".pdf":
            return DocumentExtractor.extract_text_from_file(file_path)

        # If Scanned Image (JPG, PNG, JPEG)
        elif path.suffix.lower() in [".jpg", ".jpeg", ".png"]:
            return OCRService._extract_from_image(path)

        else:
            raise ValueError(f"Unsupported format: {path.suffix}")

    @staticmethod
    def _extract_from_image(image_path: Path) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                img = Image.open(image_path)
                model_name = os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        "You are an accurate OCR engine for student exam answer sheets. "
                        "Transcribe all handwritten and typed text verbatim without modifying it. "
                        "Preserve question numbers (e.g., Q1, Ans 2, 3.).",
                        img
                    ]
                )
                return response.text.strip()
            except Exception as e:
                print(f"[Warning] Vision OCR failed: {e}. Fallback to basic image text placeholder.")

        # Fallback if no vision key
        return f"[Transcribed text from image: {image_path.name}]"