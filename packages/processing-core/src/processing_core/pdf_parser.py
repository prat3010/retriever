import pdfplumber


def extract_text_from_pdf(storage_path: str) -> str:
    text_runs = []
    with pdfplumber.open(storage_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=True)
            if page_text:
                text_runs.append(page_text)
    return "\n--- Page Break ---\n".join(text_runs)


def extract_text_from_file(storage_path: str) -> str:
    if storage_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(storage_path)
    with open(storage_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
