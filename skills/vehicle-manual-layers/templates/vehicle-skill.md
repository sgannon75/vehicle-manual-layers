---
name: MAKE-MODEL-YEAR-manual
description: "Use when operating the YEAR MAKE MODEL. Local owner's manual, three layers."
version: 1.0
source: Local owner's-manual PDF (fill path)
---

# YEAR MAKE MODEL Owner's Manual Knowledge Base

**Vehicle:** year, make, model, powertrain (gas / PHEV / EV). Trim and seating if it matters.

**Source PDF:** `C:/absolute/path/to/owners-manual.pdf`

**Manual edition / market / SHA-256:** fill from the extraction manifest and confirm applicability. If the hash changes, rebuild references and reverify standing facts.

**Three-layer lookup (stop at the first layer that answers):**
1. **This file (`SKILL.md`)** — source-backed standing facts and distilled how-to. Stop here for routine questions only. For safety-sensitive procedures, warning lights, towing, jacking, and specifications, check the underlying manual passage for warnings and conditions.
2. **`references/`** — full manual text, split by chapter. Search this folder. Start with `references/00-manifest.md`. Cite `<!-- pdf-page N -->`.
3. **The PDF** — figures, switch glyphs, and tables Layer 2 dropped. Open the page in the Layer 2 marker. Do not comb the whole book.

Preserve conditions and step order. Sparse or multi-column text and missing diagram labels require PDF inspection. Cite answers as "Owner's Manual, PDF page N (printed X when available)". PDF markers are one-based; convert if the viewer uses zero-based indices.

**Do not web-search** manufacturer sites, forums, or EPA pages for how *this* car operates. If Layers 1-3 still lack it, say so and ask the owner.

Re-extract Layer 2 after a new manual edition: `python scripts/extract_manual.py --pdf "..." --out references`

## Standing facts (this vehicle, not the whole book)

- Manufacturer facts: value, applicability/conditions, and source PDF page for each fuel or charging recommendation.
- Owner-confirmed equipment: trim, seating, installed options, and confirmation source/date.
- Owner preferences: preferred charging cap and other settings, explicitly separate from manufacturer recommendations.
- Do not mix this skill with a different household vehicle's manual.

## Distilled index

Short bullets only. Point long procedures at Layer 2 files.
