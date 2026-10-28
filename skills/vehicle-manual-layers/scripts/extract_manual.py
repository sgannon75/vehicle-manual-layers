#!/usr/bin/env python3
"""Extract an owner's-manual PDF into chapter Markdown (Layer 2).

Requires a text-layer PDF. Does not OCR. Does not fetch the web.

  python extract_manual.py --pdf MANUAL.pdf --out /path/to/skill/references
"""
from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

from pypdf import PdfReader

EDITION_RE = re.compile(
    r".*_Edition\d+_\w+\s+\d{4}-\d{1,2}-\d{1,2}\s+\d{2}:\d{2}:\d{2}"
)
PRINTED_PAGE_RE = re.compile(r"^\d{1,2}-\d{1,3}$")
LIGATURES = {
    chr(0xFB00): "ff",
    chr(0xFB01): "fi",
    chr(0xFB02): "fl",
    chr(0xFB03): "ffi",
    chr(0xFB04): "ffl",
    chr(0x2013): "-",
    chr(0x2014): "-",
    chr(0x2018): "'",
    chr(0x2019): "'",
    chr(0x201C): '"',
    chr(0x201D): '"',
    chr(0x00A0): " ",
}


def slugify(title: str) -> str:
    s = title.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")[:48] or "section"


def walk(items, reader: PdfReader):
    out = []
    i = 0
    while i < len(items or []):
        it = items[i]
        if isinstance(it, list):
            i += 1
            continue
        title = (getattr(it, "title", None) or str(it)).strip()
        try:
            page = reader.get_destination_page_number(it)
        except Exception:
            page = None
        children = []
        if i + 1 < len(items) and isinstance(items[i + 1], list):
            children = walk(items[i + 1], reader)
            i += 2
        else:
            i += 1
        if page is not None:
            out.append({"title": title, "page": page, "children": children})
    return out


def clean_page(text: str) -> tuple[str, str | None]:
    for src, dst in LIGATURES.items():
        text = text.replace(src, dst)
    text = unicodedata.normalize("NFKC", text)
    text = EDITION_RE.sub("", text)
    text = re.sub(r"\bo\s+ff\b", "off", text, flags=re.IGNORECASE)
    lines = [ln.rstrip() for ln in text.splitlines()]
    printed = None
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and PRINTED_PAGE_RE.match(lines[-1].strip()):
        printed = lines[-1].strip()
        lines.pop()
        while lines and not lines[-1].strip():
            lines.pop()
    cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(lines).strip())
    return cleaned, printed


def extract_range(reader: PdfReader, start: int, end: int) -> str:
    parts = []
    for idx in range(start, end):
        raw = reader.pages[idx].extract_text() or ""
        body, printed = clean_page(raw)
        pdf_page = idx + 1
        marker = f"<!-- pdf-page {pdf_page}"
        if printed:
            marker += f" / {printed}"
        marker += " -->"
        if len(body) < 40:
            parts.append(f"{marker}\n\n[figure omitted — see PDF page {pdf_page}]\n")
        else:
            parts.append(f"{marker}\n\n{body}\n")
    return "\n".join(parts).strip() + "\n"


def jobs_from_outline(tops, n_pages: int, max_pages: int):
    jobs = []
    if tops and tops[0]["page"] > 0:
        jobs.append(("00-front-matter", "Front matter", 0, tops[0]["page"]))
    for i, ch in enumerate(tops):
        start = ch["page"]
        end = tops[i + 1]["page"] if i + 1 < len(tops) else n_pages
        span = end - start
        prefix = f"{i + 1:02d}"
        kids = [k for k in ch["children"] if k["page"] >= start]
        if span > max_pages and kids:
            bundles = []
            b_start, b_title, b_page = 0, kids[0]["title"], kids[0]["page"]
            for j, kid in enumerate(kids):
                nxt = kids[j + 1]["page"] if j + 1 < len(kids) else end
                if j > 0 and (nxt - b_page) > max_pages:
                    bundles.append((b_title, b_page, kid["page"]))
                    b_title, b_page = kid["title"], kid["page"]
                b_start = j
            bundles.append((b_title, b_page, end))
            # include chapter intro before first child
            if bundles[0][1] > start:
                jobs.append(
                    (f"{prefix}a-{slugify(ch['title'])}-intro", ch["title"] + " (intro)", start, bundles[0][1])
                )
            letters = "abcdefghijklmnopqrstuvwxyz"
            for k, (title, s, e) in enumerate(bundles):
                letter = letters[k] if k < len(letters) else str(k)
                jobs.append((f"{prefix}{letter}-{slugify(title)}", f"{ch['title']}: {title}", s, e))
        else:
            jobs.append((f"{prefix}-{slugify(ch['title'])}", ch["title"], start, end))
    return jobs


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-pages", type=int, default=90)
    args = ap.parse_args()
    pdf = args.pdf.expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    reader = PdfReader(str(pdf))
    n = len(reader.pages)
    tops = walk(reader.outline, reader)
    if not tops:
        raise SystemExit("No PDF bookmarks. Add an outline or split by hand.")

    out = args.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("*.md"):
        old.unlink()

    jobs = jobs_from_outline(tops, n, args.max_pages)
    manifest = [
        "# Manual - Layer 2 file map",
        "",
        f"Source PDF: `{pdf}`",
        f"PDF pages: {n}",
        "",
        "Lookup: Layer 1 SKILL.md -> this folder -> Layer 3 the PDF page in the marker.",
        "",
        "| File | Section | PDF pages |",
        "| --- | --- | --- |",
    ]
    for slug, title, start, end in jobs:
        if start >= end:
            continue
        body = extract_range(reader, start, end)
        header = (
            f"# {title}\n\n"
            f"- Source PDF: `{pdf}`\n"
            f"- PDF pages: {start + 1}-{end} (inclusive)\n"
            f"- Figures/switch glyphs are omitted; use the PDF page marker when Layer 2 is not enough.\n\n"
            f"---\n\n"
        )
        path = out / f"{slug}.md"
        path.write_text(header + body, encoding="utf-8")
        manifest.append(f"| `{slug}.md` | {title} | {start + 1}-{end} |")
        print(f"wrote {path.name:42} pages {start+1:3}-{end:<3}  {path.stat().st_size:7} bytes")

    manifest.append("")
    manifest.append("Re-extract: python scripts/extract_manual.py --pdf <pdf> --out references")
    (out / "00-manifest.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    print("files", len(jobs), "pages", n)


if __name__ == "__main__":
    main()
