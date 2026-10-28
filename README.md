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

4. Point Layer 1 at Layer 2. Verify one control (parking brake, Auto Hold, a warning light) before you trust it.

## What not to publish

- OEM PDFs
- Extracted chapter Markdown of a copyrighted manual

Share **this recipe**. Each owner uses the book they already have the right to use.

## License

MIT (the recipe and script only).
