#!/usr/bin/env python3
"""Extract an owner's-manual PDF into chapter Markdown (Layer 2).

Requires a text-layer PDF. Does not OCR. Does not fetch the web.

  python extract_manual.py --pdf MANUAL.pdf --out /path/to/skill/references
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tempfile
import os
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
            parts.append(f"{marker}\n\n{body}\n\n[little or no text extracted — inspect PDF page {pdf_page}; OCR may be needed]\n")
        else:
            parts.append(f"{marker}\n\n{body}\n")
    return "\n".join(parts).strip() + "\n"


def jobs_from_outline(tops, n_pages: int, max_pages: int):
    if max_pages <= 0:
        raise ValueError("max-pages must be positive")
    if n_pages <= 0:
        raise ValueError("PDF has no pages")
    # Normalize duplicate/out-of-order destinations; every physical page belongs
    # to exactly one range. Nested headings supply preferred split boundaries.
    chapters = {}
    for chapter in tops:
        page = chapter["page"]
        if not 0 <= page < n_pages:
            raise ValueError(f"Invalid bookmark page: {page}")
        chapters.setdefault(page, chapter)
    ordered = sorted(chapters.items())
    if not ordered or ordered[0][0] > 0:
        ordered.insert(0, (0, {"title": "Front matter" if ordered else "Manual", "children": []}))
    jobs = []
    def boundaries(children):
        for child in children:
            yield child["page"]
            yield from boundaries(child["children"])
    for i, (start, ch) in enumerate(ordered):
        end = ordered[i + 1][0] if i + 1 < len(ordered) else n_pages
        cuts = sorted(set(p for p in boundaries(ch["children"]) if start < p < end))
        part = 1
        while start < end:
            stop = min(start + max_pages, end)
            if stop < end:
                candidates = [p for p in cuts if start < p <= stop]
                if candidates:
                    stop = candidates[-1]
            slug = f"{i+1:02d}-{part:03d}-{slugify(ch['title'])}"
            jobs.append((slug, ch["title"], start, stop))
            start, part = stop, part + 1
    cursor = 0
    for _, _, start, end in jobs:
        if start != cursor or not 0 < end - start <= max_pages:
            raise ValueError("Invalid page coverage")
        cursor = end
    if cursor != n_pages:
        raise ValueError("Incomplete page coverage")
    return jobs


def publish(out: Path, files: dict[str, str], metadata: dict) -> None:
    """Stage first; only replace tracked, unmodified generated files.

    Each replacement is atomic. A failed multi-file publication rolls back the
    prior bytes; this is not a crash-atomic directory transaction.
    """
    state_name = ".vehicle-manual-generated.json"
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / state_name
    if out.is_symlink() or state_path.is_symlink():
        raise ValueError("Output and tracking file must not be symlinks")
    previous = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {"files": {}}
    tracked = previous["files"]
    for name in set(tracked) | set(files):
        if Path(name).name != name or not name.endswith(".md") or name == "SKILL.md":
            raise ValueError(f"Unsafe generated filename: {name}")
        target = out / name
        if target.is_symlink():
            raise ValueError(f"Refusing symlink: {name}")
        if target.exists():
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            if tracked.get(name) != digest:
                raise ValueError(f"Preserving untracked or edited file: {name}; use a fresh output folder")
    encoded = {name: body.encode("utf-8") for name, body in files.items()}
    metadata["files"] = {name: hashlib.sha256(body).hexdigest() for name, body in encoded.items()}
    encoded[state_name] = (json.dumps(metadata, indent=2) + "\n").encode("utf-8")
    names = set(tracked) | set(encoded)
    backup = {name: (out / name).read_bytes() if (out / name).exists() else None for name in names}
    with tempfile.TemporaryDirectory(prefix=".manual-stage-", dir=out.parent) as staging:
        stage = Path(staging)
        for name, body in encoded.items():
            (stage / name).write_bytes(body)
        try:
            for name in encoded:
                if name != state_name:
                    os.replace(stage / name, out / name)
            for name in set(tracked) - set(files):
                (out / name).unlink(missing_ok=True)
            os.replace(stage / state_name, state_path)
        except Exception:
            for name, body in backup.items():
                if body is None:
                    (out / name).unlink(missing_ok=True)
                else:
                    (stage / name).write_bytes(body)
                    os.replace(stage / name, out / name)
            raise


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-pages", type=int, default=90)
    ap.add_argument("--edition", default="unspecified")
    ap.add_argument("--market", default="unspecified")
    args = ap.parse_args()
    if args.max_pages <= 0:
        ap.error("--max-pages must be positive")
    pdf = args.pdf.expanduser().resolve()
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    reader = PdfReader(str(pdf))
    n = len(reader.pages)
    tops = walk(reader.outline, reader)

    out = args.out.expanduser().resolve()
    jobs = jobs_from_outline(tops, n, args.max_pages)
    fingerprint = hashlib.sha256(pdf.read_bytes()).hexdigest()
    files = {}
    manifest = [
        "# Manual - Layer 2 file map",
        "",
        f"Source PDF: `{pdf}`",
        f"PDF pages: {n}",
        f"SHA-256: `{fingerprint}`",
        f"Edition: {args.edition}; market/region: {args.market}",
        "Splitting: bookmarks with page-window fallback" if tops else "Splitting: page windows (no bookmarks)",
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
        files[path.name] = header + body
        manifest.append(f"| `{slug}.md` | {title} | {start + 1}-{end} |")
        print(f"prepared {path.name:42} pages {start+1:3}-{end:<3}")

    manifest.append("")
    manifest.append("Re-extract: python scripts/extract_manual.py --pdf <pdf> --out references")
    files["00-manifest.md"] = "\n".join(manifest) + "\n"
    publish(out, files, {"source_pdf": str(pdf), "sha256": fingerprint,
                         "edition": args.edition, "market": args.market})
    print("files", len(jobs), "pages", n)


if __name__ == "__main__":
    main()
