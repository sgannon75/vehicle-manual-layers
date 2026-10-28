---
name: vehicle-manual-layers
description: "Use when building a 3-layer vehicle manual skill from PDF."
version: 1.0.0
author: Sean Gannon + Darren
license: MIT
metadata:
  hermes:
    tags: [vehicle, owners-manual, pdf, skills, knowledge-base]
---

# Vehicle owner's-manual skill (three layers)

Factory recipe. Input: **this vehicle's official owner's-manual PDF**. Output: a per-vehicle skill with a thin Layer 1, searchable chapter Markdown (Layer 2), and the PDF as Layer 3 for figures.

Do **not** ship or copy OEM manuals. Share **this recipe**. Each owner uses their own PDF.

Compatible with the [Agent Skills](https://agentskills.io/specification) `SKILL.md` shape, so the same files work in Hermes and in other agents that load skills (Claude Code, Codex, etc.). Hermes-specific commands are marked.

## When to Use

- User has a local owner's-manual PDF and wants the assistant to answer from **this car**, not the web.
- Building or rebuilding a per-vehicle skill.
- Distilled `/learn` notes are too thin for a control, warning light, or procedure.

Do **not** use this to scrape manufacturer websites into a public skill.

## The three layers

Stop at the first layer that answers routine questions. For safety-sensitive procedures, warning lights, towing, jacking, or specifications, check the source passage for conditions and warnings even if Layer 1 appears to answer. Inspect the PDF whenever layout, tables, or figures could affect meaning.

1. **`SKILL.md` (Layer 1)** — standing facts for *this* vehicle (year, trim, fuel, charge limits, seating) plus a short distilled index. Loaded every time the vehicle skill is used. Keep it small.
2. **`references/*.md` (Layer 2)** — full text extract, one file per manual chapter (split a 200+ page chapter). Search it. Cite `<!-- pdf-page N -->`.
3. **The PDF (Layer 3)** — source of truth for **figures, switch glyphs, and tables** the extract dropped. Open the **page from the Layer 2 marker**. Do not comb 700 pages.

Never fill a gap from manufacturer sites, forums, or fueleconomy.gov for how *this* car operates.

## Procedure (next vehicle is a run)

### 0. Preconditions

- PDF on disk. Prefer the owner's copy, not a random internet file.
- Confirm a **text layer** (`pypdf` extract on a middle page returns real sentences). If it is a scan, OCR first; do not pretend extract worked.
- Confirm outline/bookmarks if possible. Bookmarks make chapter splits. No bookmarks: split by printed part titles or equal page windows and say so in the manifest.

### 1. Create the vehicle skill (Layer 1 stub)

New skill named for the vehicle (`make-model-year-manual`). Copy `templates/vehicle-skill.md` and fill:

- Year, make, model, powertrain (gas / PHEV / EV)
- Manufacturer facts with source pages (fuel grade, charging recommendations), separately from owner-confirmed equipment and preferences (seating, preferred charge cap). Record unknowns rather than guessing.
- Manual edition, market/region, and SHA-256 from the extraction manifest; confirm the manual applies to this vehicle.
- Absolute PDF path
- Rule: Layer 1 → search `references/` → PDF page in the marker
- Rule: do not web-search this car's operation

Hermes: `skill_manage` create, then patch. Other agents: write `SKILL.md` in their skills dir.

### 2. Extract Layer 2

From this factory skill:

```bash
python scripts/extract_manual.py --pdf "/path/to/manual.pdf" --out "/path/to/vehicle-skill/references" --max-pages 90
```

The script:

- Walks PDF bookmarks for top-level chapters
- Uses nested bookmarks where possible, with page-window fallback to enforce `--max-pages` and cover every page exactly once; works without bookmarks
- Writes `00-manifest.md` plus `NN-slug.md` with `<!-- pdf-page N / printed -->` markers
- Preserves sparse text and flags pages with little or no extracted text for PDF inspection or OCR; this does not prove a figure exists
- Does not OCR
- Stages extraction before publication, tracks generated files and their hashes, and refuses to overwrite untracked or edited files. Use a fresh folder to migrate old untracked extracts. Individual replacements are atomic, with rollback on caught errors; interruption or concurrent runs are not supported as a transaction.
- Records source path, SHA-256, edition and market (`--edition` and `--market`) in the manifest

Copy the script into the vehicle skill's `scripts/` if you want that car to re-extract without this factory skill. Re-run after a new manual edition.

### 3. Wire Layer 1 to Layer 2

Patch the vehicle `SKILL.md`:

- Three-layer lookup at the top
- File map (or point at the generated `references/00-manifest.md` in that vehicle skill)
- Distilled bullets that used to say "see manual" now point at the Layer 2 file

### 4. Verify before calling it done

Pick a control the distilled notes under-specify (parking brake, Auto Hold, a warning light). Confirm:

- Layer 2 search hits the right chapter file
- A `<!-- pdf-page N -->` marker exists
- Inspect the actual PDF page and verify the answer preserves step order, conditions, warnings, and applicability; missing text is a reason to inspect, never proof of correctness
- Check at least one warning, one figure-dependent control, and one table or multi-column passage. Review sparse-page flags throughout the extract; a text-bearing middle page does not rule out scanned pages elsewhere. OCR or inspect affected pages before relying on them.
- Present citations as "Owner's Manual, PDF page N (printed X when available)" rather than exposing HTML comments. The PDF page is one-based; viewer APIs may require a zero-based index.

### 5. Keep cars isolated

One skill per vehicle. Do not answer one household car from another car's extract.

## What Layer 1 is for

Facts that are **this car**, not the whole book:

- Fuel (regular vs premium), charge limits, seating (captains vs bench)
- "Do not web-search" and the PDF path
- Short how-to that is used weekly

Every distilled manufacturer fact or how-to needs a source page and applicable conditions. Keep owner preferences separate from manufacturer recommendations. If the PDF hash changes, re-extract and reverify Layer 1 before using cached facts.

If a procedure needs warnings, conditions, or cancel rules, leave it in Layer 2.

## Sharing this sauce (not the manuals)

Share **this factory skill** (`SKILL.md` + `scripts/extract_manual.py` + `templates/`). Never publish OEM PDFs or Layer 2 extracts of a copyrighted manual.

**Portable unit:** the `SKILL.md` folder. Agent Skills spec: https://agentskills.io/specification

**Hermes install paths (pick one, in this order):**

1. GitHub repo that contains only the factory skill ↔ others `hermes skills tap add <owner/repo>` then `hermes skills install …`
2. `hermes skills publish <path> --to github --repo <owner/repo>` onto Skills Hub
3. Direct `hermes skills install https://…/SKILL.md`

Do not PR household vehicle skills into Hermes bundled catalogs. The factory recipe is what to share; the car files stay private.

**Other agents:** drop the same folder into their skills directory (Claude Code `~/.claude/skills`, etc.). They need a PDF text extractor; the Python script is the reference implementation (`pypdf`).

**Do not amplify with:** a dump of extracted OEM chapters, or "download this manual." Point at the recipe. Each owner brings the PDF they already have the right to use.

## Pitfalls

- **Scan PDFs.** No text layer → garbage Layer 2. OCR or stop.
- **One giant Markdown file.** Reloads the whole book into context. Chapter files exist so search is cheap.
- **`/learn` alone.** Distills to a few bullets (Auto Hold became two lines). That is Layer 1, not the book.
- **Web fill.** Wrong year, wrong trim, wrong powertrain. Forbidden for operation questions.
- **Figures.** Switch drawings vanish. Layer 3 is required, not optional.
- **Trim coverage.** Manuals describe every option. Layer 1 must record what *this* vehicle has.
- **Huge chapters.** "When Driving" / "Driving" often exceed 200 pages. Always split.
- **Copyright.** Recipe is MIT. The OEM PDF is not yours to redistribute.

## Verification

Factory skill is ready when a new PDF can be pointed at `extract_manual.py` and a vehicle `SKILL.md` stub, and a sample control is answerable from Layer 2 with a PDF page citation.
