import pdfplumber
from src.domain.abstractions.ingestion import DocumentParser


class LayoutPdfParser(DocumentParser):
    def parse_file(self, file_path: str, mime_type: str) -> str:
        """Extract layout-preserving unstructured text from PDF and text documents."""
        if "pdf" in mime_type.lower():
            text_runs = []
            # Utilize pdfplumber to parse text layout dynamically
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text(layout=True)
                    if page_text:
                        text_runs.append(page_text)
            return "\n--- Page Break ---\n".join(text_runs)
        else:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
