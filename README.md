# vehicle-manual-layers

A **factory recipe** for personal AI assistants: turn **your** vehicle owner's-manual PDF into a three-layer skill.

Bring your own PDF. This repo does **not** include any manufacturer manuals.

Works with [Hermes](https://hermes-agent.nousresearch.com/) and any agent that loads [Agent Skills](https://agentskills.io/specification) (`SKILL.md`).

## Why

Owner's manuals are 600-700 pages. Distilled summaries miss the button you actually pressed. The web is the wrong year, trim, or powertrain.

Three layers, stop at the first that answers:

1. **Layer 1** (`SKILL.md`) — standing facts for *this* car (fuel, charge limit, seating) plus a short index
2. **Layer 2** (`references/*.md`) — full text, split by chapter, searchable, with PDF page markers
3. **Layer 3** — the original PDF, opened at the marked page, for figures and switch drawings

## Install (Hermes)

```bash
hermes skills tap add sgannon75/vehicle-manual-layers
hermes skills install sgannon75/vehicle-manual-layers/vehicle-manual-layers
```

Or copy `skills/vehicle-manual-layers/` into your agent's skills directory.

## Use

1. Put your official owner's-manual PDF on disk (text layer, not a scan).
2. Create a per-vehicle skill from `templates/vehicle-skill.md`.
3. Extract chapters:

```bash
python skills/vehicle-manual-layers/scripts/extract_manual.py \
  --pdf "/path/to/owners-manual.pdf" \
  --out "/path/to/your-vehicle-skill/references"
```

Requires Python 3 and `pypdf`.

Optional source metadata: add `--edition "2026 edition" --market "US"`.
The manifest records the source PDF SHA-256. Bookmark splits use page-window
fallback so `--max-pages` (default 90) is enforced even without bookmarks.

Regeneration preserves unrelated Markdown and refuses to overwrite edited or
untracked files with matching names. For extracts made with the old script, use
a fresh output folder and inspect it before switching your vehicle skill over.
Extraction completes in staging before generated files are replaced; caught
publication errors roll back prior bytes. Do not run concurrent extractions into
the same folder. A process or machine crash is not a directory-wide transaction.

4. Point Layer 1 at Layer 2. Verify a warning, a figure-dependent control, and a table or multi-column passage against the actual PDF. Inspect sparse-page flags; mixed scanned/text PDFs may need partial OCR. Keep source pages on distilled facts and separate owner preferences from manufacturer recommendations.

## Tests

Install `pypdf`, then run `python -m unittest discover -s tests -v`.
Tests use synthetic content only; no OEM manual is included. They cover page
coverage, size limits, sparse text, safe regeneration, and publication rollback.
Real-manual visual checks remain necessary for diagrams and reading order.

## What not to publish

- OEM PDFs
- Extracted chapter Markdown of a copyrighted manual

Share **this recipe**. Each owner uses the book they already have the right to use.

## License

MIT (the recipe and script only).
