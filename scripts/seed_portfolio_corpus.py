#!/usr/bin/env python3
"""Seed Portfolio Knowledge Corpus into live Retriever VPS.

Compiles the Master Technical Dossier from website JSON data,
collects whitelisted architecture docs and blog posts,
and batch-ingests them into the prateeq_portfolio tenant on rag.prateeq.in.
"""

import json
from pathlib import Path
import shutil
import time
import urllib.error
import urllib.request

TENANT_ID = "6797e2c8-745a-4bd1-aa4c-3854b8d79c22"
API_KEY = "ret_live_TaaRP0w94H8.a3_CjGsoQY57Fy5bv9Kk40zfUOoH4ak2"
TARGET_URL = "https://rag.prateeq.in"

WEB_ROOT = Path("/Users/prateeksharma/Developer/Prateek_website")
RETRIEVER_ROOT = Path("/Users/prateeksharma/Developer/retriever")
STAGING_DIR = Path("/tmp/prateeq_dogfood_corpus")


def generate_dossier() -> Path:
    """Compile structured JSON data into a comprehensive Markdown dossier."""
    with open(WEB_ROOT / "src/data/resume.json") as f:
        resume = json.load(f)
    with open(WEB_ROOT / "src/data/projects.json") as f:
        projects = json.load(f)
    with open(WEB_ROOT / "src/data/skills.json") as f:
        skills = json.load(f)
    with open(WEB_ROOT / "src/data/intakeQuestionnaireDefaults.json") as f:
        intake = json.load(f)

    lines = [
        "# PRATEEQ SHARMA — MASTER TECHNICAL & ARCHITECTURAL DOSSIER",
        "",
        "## 1. Biography & Professional Summary",
        f"- **Name**: {resume.get('name', 'Prateeq Sharma')}",
        f"- **Title**: {resume.get('title', 'Forward Deployed AI Engineer')}",
        f"- **Email**: {resume.get('email', 'prateeqsharma@gmail.com')}",
        f"- **Phone**: {resume.get('phone', '+91 9050433260')}",
        f"- **GitHub**: {resume.get('github', 'https://github.com/prat3010')}",
        "- **Location**: Based in India, working remotely with clients worldwide.",
        "",
        "### Professional Philosophy & Manifesto",
        f"**Developer Persona**: {resume.get('about', {}).get('developer', {}).get('noir', '')}",
        "",
        f"**Business Persona**: {resume.get('about', {}).get('business', {}).get('noir', '')}",
        "",
        "## 2. Verified Technical Skills & Stack",
    ]

    lines.append("\n## 2. Verified Technical Skills & Stack\n")
    if isinstance(skills, list):
        for item in skills:
            name = item.get("name", "")
            name_biz = item.get("name_business", "")
            desc = item.get("description", "")
            desc_biz = item.get("description_business", "")
            cat = item.get("category", "")
            lines.append(f"### Skill: {name} (Business: {name_biz}) [Category: {cat}]")
            lines.append(f"- **Developer Details**: {desc}")
            lines.append(f"- **Business Value**: {desc_biz}")
            lines.append("")

    lines.append("\n## 3. Flagship Projects & Case Studies\n")
    project_list = projects if isinstance(projects, list) else projects.get("projects", [])
    for p in project_list:
        title = p.get("title", "")
        role = p.get("systemRole", "Lead Architect")
        dev_desc = p.get("longDescription", p.get("description", ""))
        biz_desc = p.get("longDescription_business", p.get("description_business", ""))
        tags = ", ".join(p.get("tags", []))
        gh = p.get("githubUrl", "")
        live = p.get("liveUrl", "")
        highlights = p.get("architectureHighlights", [])

        lines.append(f"### Project: {title}")
        lines.append(f"- **System Role**: {role}")
        lines.append(f"- **Technical Architecture**: {dev_desc}")
        lines.append(f"- **Business Value**: {biz_desc}")
        lines.append(f"- **Tags**: {tags}")
        if gh:
            lines.append(f"- **GitHub**: {gh}")
        if live:
            lines.append(f"- **Live URL**: {live}")
        if highlights:
            lines.append("- **Key Architectural Highlights**:")
            for h in highlights:
                lines.append(f"  * {h}")
        lines.append("")

    lines.append("\n## 4. Commercial Offerings, Scoping & Pricing Models\n")
    lines.append("Prateeq offers transparent, fixed-price project scoping via the interactive /scoping engine on prateeq.in.\n")
    for eng in intake.get("engines", []):
        lbl = eng.get("label", "")
        eid = eng.get("id", "")
        desc = eng.get("description", "")
        p_inr = eng.get("basePriceINR", 0)
        p_usd = eng.get("basePriceUSD", 0)
        d_min = eng.get("estimatedDaysMin", 3)
        d_max = eng.get("estimatedDaysMax", 7)

        lines.append(f"### Base Engine: {lbl} (ID: {eid})")
        lines.append(f"- **Description**: {desc}")
        lines.append(f"- **Base Investment**: ₹{p_inr:,} INR / ${p_usd:,} USD")
        lines.append(f"- **Delivery Velocity**: ~{d_min} to {d_max} business days")
        lines.append("")

    dossier_path = STAGING_DIR / "PRATEEQ_KNOWLEDGE_DOSSIER.md"
    dossier_path.write_text("\n".join(lines), encoding="utf-8")
    return dossier_path


def stage_corpus() -> list[Path]:
    """Collect whitelisted documentation, blog posts, and dossier into staging."""
    if STAGING_DIR.exists():
        shutil.rmtree(STAGING_DIR)
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    staged_files: list[Path] = []

    # 1. Master Dossier
    dossier_path = generate_dossier()
    staged_files.append(dossier_path)

    # 2. Portfolio Architecture Docs
    docs_to_include = [
        "01_Vision_and_Philosophy.md",
        "04_Adaptive_Portfolio_Experience.md",
        "06_Adaptive_Identity_System.md",
        "07_Content_Strategy.md",
        "08_Information_Architecture.md",
        "10_Content_Platform_Architecture.md",
        "12_AI_Integration_Strategy.md",
        "15_Performance_and_Accessibility.md",
        "16_Security_and_Privacy.md",
        "24_RAG_App_Studio_PRD.md",
        "25_SOTA_Scoping_Engine_PRD.md",
        "30_Interactive_Diagnostics_Terminal_PRD.md",
        "99_DECISIONS.md",
    ]
    for doc_name in docs_to_include:
        src = WEB_ROOT / "docs" / doc_name
        if src.exists():
            dest = STAGING_DIR / f"arch_{doc_name}"
            shutil.copy2(src, dest)
            staged_files.append(dest)

    # 3. Blog Posts
    posts_dir = WEB_ROOT / "src" / "content" / "posts"
    if posts_dir.exists():
        for post in posts_dir.glob("*.md"):
            dest = STAGING_DIR / f"blog_{post.name}"
            shutil.copy2(post, dest)
            staged_files.append(dest)

    # 4. Retriever Engine Architecture Docs
    retriever_docs = [
        ("README.md", "retriever_README.md"),
        ("docs/architecture.md", "retriever_architecture.md"),
        ("docs/cognitive/agentic_workflows_and_repl.md", "retriever_agentic_repl.md"),
        ("docs/cognitive/hybrid_search_and_fusion.md", "retriever_hybrid_search.md"),
        ("docs/benchmarks/EMPIRICAL_LOAD_BENCHMARK_REPORT.md", "retriever_benchmark_report.md"),
    ]
    for rel_path, dest_name in retriever_docs:
        src = RETRIEVER_ROOT / rel_path
        if src.exists():
            dest = STAGING_DIR / dest_name
            shutil.copy2(src, dest)
            staged_files.append(dest)

    return staged_files


def split_markdown_sections(text: str, max_chars: int = 12000) -> list[str]:
    """Split markdown along heading boundaries, keeping parts under max_chars."""
    import re

    if len(text) <= max_chars:
        return [text]

    sections = re.split(r"\n(?=#{1,3}\s)", text)
    refined_sections: list[str] = []
    for sec in sections:
        if len(sec) > max_chars:
            paras = sec.split("\n\n")
            curr = ""
            for p in paras:
                if len(curr) + len(p) > max_chars and curr:
                    refined_sections.append(curr)
                    curr = p
                else:
                    curr = curr + "\n\n" + p if curr else p
            if curr:
                refined_sections.append(curr)
        else:
            refined_sections.append(sec)

    parts: list[str] = []
    current_part = ""
    for sec in refined_sections:
        if len(current_part) + len(sec) > max_chars and current_part:
            parts.append(current_part.strip())
            current_part = sec
        else:
            current_part = current_part + "\n\n" + sec if current_part else sec
    if current_part.strip():
        parts.append(current_part.strip())
    return parts


def upload_content(filename: str, content_text: str) -> bool:
    """Upload content string to Retriever synchronous raw ingestion endpoint."""
    payload = json.dumps({
        "title": filename,
        "content": content_text,
        "mime_type": "text/markdown",
        "tags": ["portfolio", "knowledge_base"],
    }).encode("utf-8")

    url = f"{TARGET_URL}/v1/tenants/{TENANT_ID}/documents/raw"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "Content-Length": str(len(payload)),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            chunks = data.get("chunk_count", 0)
            status = data.get("status", "PROCESSED")
            print(f"  ✓ Indexed: {filename} ({len(content_text):,} chars) -> {chunks} chunks [{status}]")
            return True
    except urllib.error.HTTPError as e:
        print(f"  ❌ Error {e.code} uploading {filename}: {e.read().decode('utf-8', errors='ignore')}")
        return False
    except Exception as e:
        print(f"  ❌ Failed uploading {filename}: {e}")
        return False


def upload_file(file_path: Path, indexed: set[str]) -> bool:
    """Upload document, splitting into sections if file exceeds 12KB."""
    try:
        content_text = file_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  ❌ Failed reading {file_path.name}: {e}")
        return False

    if len(content_text) > 12000:
        parts = split_markdown_sections(content_text, max_chars=12000)
        print(f"  📄 Splitting large doc {file_path.name} ({len(content_text):,} chars) into {len(parts)} sections...")
        all_ok = True
        for idx, part in enumerate(parts, start=1):
            part_filename = f"{file_path.stem}_part{idx}.md"
            if part_filename in indexed:
                print(f"    ⏭️ Already indexed: {part_filename}")
                continue
            ok = upload_content(part_filename, part)
            if not ok:
                all_ok = False
            time.sleep(2.0)
        return all_ok

    if file_path.name in indexed:
        print(f"  ⏭️ Already indexed: {file_path.name}")
        return True

    ok = upload_content(file_path.name, content_text)
    time.sleep(2.0)
    return ok


def get_indexed_filenames() -> set[str]:
    """Retrieve set of filenames already processed and indexed in pgvector."""
    url = f"{TARGET_URL}/v1/tenants/{TENANT_ID}/documents?limit=200"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {API_KEY}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            items = data.get("items", []) if isinstance(data, dict) else data
            return {
                doc.get("filename")
                for doc in items
                if doc.get("status") == "INDEXED"
            }
    except Exception as e:
        print(f"  ⚠️ Could not query existing indexed documents: {e}")
        return set()


def main():
    print(f"🚀 Staging knowledge corpus for tenant: {TENANT_ID}...")
    staged = stage_corpus()
    print(f"📦 Staged {len(staged)} curated knowledge documents ({sum(f.stat().st_size for f in staged):,} total bytes).")

    indexed = get_indexed_filenames()
    print(f"🔍 Found {len(indexed)} already-indexed documents in vector database.")

    print("\n🛰️ Dispatching batch upload to https://rag.prateeq.in...")
    success_count = 0
    for f in staged:
        if upload_file(f, indexed):
            success_count += 1
        time.sleep(0.5)

    print(f"\n🎉 Finished: {success_count}/{len(staged)} document suites successfully active and indexed!")


if __name__ == "__main__":
    main()
