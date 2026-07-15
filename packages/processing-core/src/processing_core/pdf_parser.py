import pdfplumber


def extract_text_from_pdf(storage_path: str) -> str:
    text_runs = []
    with pdfplumber.open(storage_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=True)
            if page_text:
                text_runs.append(page_text)
    return "\n--- Page Break ---\n".join(text_runs)


def extract_tables_from_pdf(storage_path: str) -> list[dict]:
    tables = []
    with pdfplumber.open(storage_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for table in page.extract_tables():
                if table and len(table) > 1:
                    headers = table[0]
                    rows = table[1:]
                    tables.append({
                        "page": page_num + 1,
                        "headers": [h.strip() if h else "" for h in headers],
                        "rows": [[c.strip() if c else "" for c in row] for row in rows],
                    })
    return tables


def extract_text_from_file(storage_path: str) -> str:
    if storage_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(storage_path)
    with open(storage_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
