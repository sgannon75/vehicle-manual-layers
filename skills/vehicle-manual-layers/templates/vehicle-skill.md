---
name: MAKE-MODEL-YEAR-manual
description: "Use when operating the YEAR MAKE MODEL. Local owner's manual, three layers."
version: 1.0
source: Local owner's-manual PDF (fill path)
---

# YEAR MAKE MODEL Owner's Manual Knowledge Base

**Vehicle:** year, make, model, powertrain (gas / PHEV / EV). Trim and seating if it matters.

**Source PDF:** `C:/absolute/path/to/owners-manual.pdf`

**Three-layer lookup (stop at the first layer that answers):**
1. **This file (`SKILL.md`)** — standing facts and distilled how-to. If it answers, stop.
2. **`references/`** — full manual text, split by chapter. Search this folder. Start with `references/00-manifest.md`. Cite `<!-- pdf-page N -->`.
3. **The PDF** — figures, switch glyphs, and tables Layer 2 dropped. Open the page in the Layer 2 marker. Do not comb the whole book.

**Do not web-search** manufacturer sites, forums, or EPA pages for how *this* car operates. If Layers 1-3 still lack it, say so and ask the owner.

Re-extract Layer 2 after a new manual edition: `python scripts/extract_manual.py --pdf "..." --out references`

## Standing facts (this vehicle, not the whole book)

- Fuel / charging limits / seating:
- Do not mix this skill with a different household vehicle's manual.

## Distilled index

Short bullets only. Point long procedures at Layer 2 files.
