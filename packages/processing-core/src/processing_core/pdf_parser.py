import os
from typing import Any

import pdfplumber


def convert_table_to_markdown(headers: list[str], rows: list[list[str]]) -> str:
    """Convert table headers and rows into a GitHub Flavored Markdown table."""
    if not headers and not rows:
        return ""

    clean_headers = [str(h).strip().replace("\n", " ") if h else "" for h in headers]
    if not any(clean_headers):
        # Fallback headers if empty
        max_cols = max(len(clean_headers), max((len(r) for r in rows), default=0))
        clean_headers = [f"Header {i + 1}" for i in range(max_cols)]

    header_line = "| " + " | ".join(clean_headers) + " |"
    separator_line = "| " + " | ".join(["---"] * len(clean_headers)) + " |"

    row_lines = []
    for row in rows:
        clean_row = [
            str(cell).strip().replace("\n", " ") if cell else "" for cell in row
        ]
        # Pad row cells to match header column count
        if len(clean_row) < len(clean_headers):
            clean_row.extend([""] * (len(clean_headers) - len(clean_row)))
        elif len(clean_row) > len(clean_headers):
            clean_row = clean_row[: len(clean_headers)]
        row_lines.append("| " + " | ".join(clean_row) + " |")

    return "\n".join([header_line, separator_line] + row_lines)


def extract_tables_from_pdf(storage_path: str) -> list[dict[str, Any]]:
    """Extract tables from PDF as structured grid dictionary records."""
    tables = []
    with pdfplumber.open(storage_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for table in page.extract_tables():
                if table and len(table) > 1:
                    headers = [str(h).strip() if h else "" for h in table[0]]
                    rows = [
                        [str(c).strip() if c else "" for c in row] for row in table[1:]
                    ]
                    tables.append(
                        {
                            "page": page_num + 1,
                            "headers": headers,
                            "rows": rows,
                            "markdown": convert_table_to_markdown(headers, rows),
                        }
                    )
    return tables


def extract_layout_from_pdf(storage_path: str) -> dict[str, Any]:
    """Extract layout-aware structured text, tables, and page metadata from PDF."""
    page_runs = []
    pages_meta = []
    total_tables = 0

    with pdfplumber.open(storage_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_text = page.extract_text(layout=True) or ""
            raw_tables = page.extract_tables() or []

            md_tables = []
            for t in raw_tables:
                if t and len(t) > 1:
                    headers = [str(cell).strip() if cell else "" for cell in t[0]]
                    rows = [
                        [str(cell).strip() if cell else "" for cell in row]
                        for row in t[1:]
                    ]
                    md = convert_table_to_markdown(headers, rows)
                    if md:
                        md_tables.append(md)

            total_tables += len(md_tables)
            combined_page_content = page_text
            if md_tables:
                combined_page_content += "\n\n### Document Tables\n" + "\n\n".join(
                    md_tables
                )

            if combined_page_content.strip():
                page_runs.append(
                    f"--- Page {page_num + 1} ---\n{combined_page_content}"
                )

            pages_meta.append(
                {
                    "page": page_num + 1,
                    "has_text": bool(page_text.strip()),
                    "table_count": len(md_tables),
                }
            )

    full_text = "\n\n".join(page_runs)
    return {
        "text": full_text,
        "page_count": len(pages_meta),
        "has_tables": total_tables > 0,
        "table_count": total_tables,
        "pages": pages_meta,
    }


def extract_form_fields(text: str) -> dict[str, str]:
    """Extract key-value form fields from text (e.g. 'Invoice Number: INV-001', 'Total: $500')."""
    import re

    fields: dict[str, str] = {}
    pattern = re.compile(
        r"^[ \t]*([A-Za-z0-9][A-Za-z0-9 _\-\./#]{1,50}?)[ \t]*[:=][ \t]+(.+)$"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            k = match.group(1).strip()
            v = match.group(2).strip()
            if k and v and len(k) <= 50 and len(v) <= 500:
                fields[k] = v
    return fields


def extract_structured_blocks(text: str) -> list[dict[str, Any]]:
    """Parse document text into semantic layout blocks: headings, tables, forms, and paragraphs.

    Preserves structural integrity for downstream chunking and retrieval.
    """
    import re

    blocks: list[dict[str, Any]] = []
    lines = text.splitlines()
    i = 0
    n = len(lines)

    table_pattern = re.compile(r"^[ \t]*\|(.+)\|[ \t]*$")
    separator_pattern = re.compile(r"^[ \t]*\|([ \t]*:?-+:?[ \t]*\|)+[ \t]*$")
    heading_pattern = re.compile(r"^(#{1,6})\s+(.+)$")
    kv_pattern = re.compile(
        r"^[ \t]*([A-Za-z0-9][A-Za-z0-9 _\-\./#]{1,40}?)[ \t]*[:=][ \t]+(.+)$"
    )

    current_para: list[str] = []

    def flush_para():
        nonlocal current_para
        if current_para:
            content = "\n".join(current_para).strip()
            if content:
                blocks.append(
                    {
                        "type": "paragraph",
                        "content": content,
                        "metadata": {"char_count": len(content)},
                    }
                )
            current_para = []

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_para()
            i += 1
            continue

        # 1. Heading check
        heading_match = heading_pattern.match(stripped)
        if heading_match:
            flush_para()
            level = len(heading_match.group(1))
            title = heading_match.group(2).strip()
            blocks.append(
                {
                    "type": "heading",
                    "content": stripped,
                    "metadata": {"level": level, "title": title},
                }
            )
            i += 1
            continue

        # 2. Markdown Table check
        if table_pattern.match(stripped):
            flush_para()
            table_lines = [line]
            i += 1
            while i < n and (
                table_pattern.match(lines[i].strip())
                or separator_pattern.match(lines[i].strip())
            ):
                table_lines.append(lines[i])
                i += 1

            headers = []
            if len(table_lines) >= 2:
                raw_header = table_lines[0].strip().strip("|").split("|")
                headers = [h.strip() for h in raw_header]
            table_content = "\n".join(table_lines)
            blocks.append(
                {
                    "type": "table",
                    "content": table_content,
                    "metadata": {
                        "headers": headers,
                        "rows_count": max(0, len(table_lines) - 2)
                        if len(table_lines) >= 2
                        else len(table_lines),
                        "is_markdown_table": True,
                    },
                }
            )
            continue

        # 3. Form / Key-Value block check (contiguous KV pairs, min 2)
        kv_match = kv_pattern.match(stripped)
        if kv_match:
            kv_lines = [line]
            next_idx = i + 1
            while (
                next_idx < n
                and lines[next_idx].strip()
                and kv_pattern.match(lines[next_idx].strip())
            ):
                kv_lines.append(lines[next_idx])
                next_idx += 1

            if len(kv_lines) >= 2:
                flush_para()
                form_fields = extract_form_fields("\n".join(kv_lines))
                blocks.append(
                    {
                        "type": "form",
                        "content": "\n".join(kv_lines),
                        "metadata": {
                            "fields": form_fields,
                            "field_count": len(form_fields),
                        },
                    }
                )
                i = next_idx
                continue

        # 4. Narrative line
        current_para.append(line)
        i += 1

    flush_para()
    return blocks


def extract_layout_aware_document(storage_path: str) -> dict[str, Any]:
    """Extract layout-aware document structure, preserving tables, forms, and section hierarchy."""
    base_layout = (
        extract_layout_from_pdf(storage_path)
        if storage_path.lower().endswith(".pdf")
        else {
            "text": extract_text_from_file(storage_path),
            "page_count": 1,
            "has_tables": False,
            "table_count": 0,
            "pages": [{"page": 1, "has_text": True, "table_count": 0}],
        }
    )

    full_text = base_layout.get("text", "")
    blocks = extract_structured_blocks(full_text)
    form_fields = extract_form_fields(full_text)

    table_block_count = sum(1 for b in blocks if b["type"] == "table")
    return {
        "text": full_text,
        "page_count": base_layout.get("page_count", 1),
        "has_tables": base_layout.get("has_tables", False) or table_block_count > 0,
        "table_count": max(base_layout.get("table_count", 0), table_block_count),
        "has_forms": len(form_fields) > 0,
        "form_count": sum(1 for b in blocks if b["type"] == "form"),
        "form_fields": form_fields,
        "pages": base_layout.get("pages", []),
        "structured_blocks": blocks,
    }


def extract_text_from_pdf(storage_path: str) -> str:
    """Extract layout-aware text (including formatted tables) from PDF."""
    layout = extract_layout_from_pdf(storage_path)
    return layout["text"]


TEXT_EXTENSIONS = {
    ".txt",
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".ini",
    ".toml",
    ".csv",
    ".xml",
    ".sh",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".kt",
    ".swift",
    ".sql",
    ".properties",
    ".conf",
    ".cfg",
    ".docx",
    ".xlsx",
    ".pptx",
}


def extract_text_from_docx(storage_path: str) -> str:
    """Extract text and tables from Microsoft Word (.docx) documents."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(storage_path) as z:
            if "word/document.xml" not in z.namelist():
                return ""
            xml_content = z.read("word/document.xml")
            tree = ET.fromstring(xml_content)

            paragraphs = []
            for p in tree.iter():
                if p.tag.endswith("}p"):
                    texts = [
                        elem.text
                        for elem in p.iter()
                        if elem.tag.endswith("}t") and elem.text
                    ]
                    p_text = "".join(texts).strip()
                    if p_text:
                        paragraphs.append(p_text)

            return "\n\n".join(paragraphs)
    except Exception:
        return ""


def extract_text_from_xlsx(storage_path: str) -> str:
    """Extract sheets and tabular data from Microsoft Excel (.xlsx) workbooks."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(storage_path) as z:
            # 1. Read shared strings if present
            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in z.namelist():
                sst_tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in sst_tree.iter():
                    if si.tag.endswith("}si"):
                        t_parts = [
                            t.text for t in si.iter() if t.tag.endswith("}t") and t.text
                        ]
                        shared_strings.append("".join(t_parts))

            # 2. Iterate worksheet XMLs
            sheet_files = sorted(
                [
                    name
                    for name in z.namelist()
                    if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
                ]
            )
            sheet_outputs = []

            for idx, sheet_file in enumerate(sheet_files):
                sheet_tree = ET.fromstring(z.read(sheet_file))
                rows_data = []
                for row_elem in sheet_tree.iter():
                    if row_elem.tag.endswith("}row"):
                        row_vals = []
                        for c in row_elem.iter():
                            if c.tag.endswith("}c"):
                                c_type = c.attrib.get("t")
                                v_elem = None
                                for sub in c:
                                    if sub.tag.endswith("}v"):
                                        v_elem = sub
                                        break
                                if v_elem is not None and v_elem.text:
                                    if c_type == "s":
                                        s_idx = int(v_elem.text)
                                        val = (
                                            shared_strings[s_idx]
                                            if s_idx < len(shared_strings)
                                            else ""
                                        )
                                    else:
                                        val = v_elem.text
                                    row_vals.append(str(val).strip())
                                else:
                                    row_vals.append("")
                        if any(v.strip() for v in row_vals):
                            rows_data.append(row_vals)

                if rows_data:
                    md_table = convert_table_to_markdown(
                        rows_data[0], rows_data[1:] if len(rows_data) > 1 else []
                    )
                    sheet_outputs.append(f"--- Sheet {idx + 1} ---\n{md_table}")

            return "\n\n".join(sheet_outputs)
    except Exception:
        return ""


def extract_text_from_pptx(storage_path: str) -> str:
    """Extract slide text from Microsoft PowerPoint (.pptx) presentations."""
    try:
        import zipfile
        import xml.etree.ElementTree as ET

        with zipfile.ZipFile(storage_path) as z:
            slide_files = sorted(
                [
                    name
                    for name in z.namelist()
                    if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                ]
            )
            slide_outputs = []

            for idx, slide_file in enumerate(slide_files):
                slide_tree = ET.fromstring(z.read(slide_file))
                texts = [
                    elem.text
                    for elem in slide_tree.iter()
                    if elem.tag.endswith("}t") and elem.text and elem.text.strip()
                ]
                if texts:
                    slide_outputs.append(
                        f"--- Slide {idx + 1} ---\n" + "\n".join(texts)
                    )

            return "\n\n".join(slide_outputs)
    except Exception:
        return ""


def extract_text_from_file(storage_path: str) -> str:
    if storage_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(storage_path)
    if storage_path.lower().endswith(".docx"):
        return extract_text_from_docx(storage_path)
    if storage_path.lower().endswith(".xlsx"):
        return extract_text_from_xlsx(storage_path)
    if storage_path.lower().endswith(".pptx"):
        return extract_text_from_pptx(storage_path)

    _, ext = os.path.splitext(storage_path.lower())
    if ext not in TEXT_EXTENSIONS:
        return ""

    with open(storage_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
