# Requirements — Information Architecture Studio (IAS)

## 1. Purpose

IAS takes an unstructured or lightly-structured document and turns it into a
themed, presentation-quality artifact, while automatically figuring out what
*kind* of document it is and which parts of it matter most.

## 2. Functional requirements

### 2.1 Input

- FR-1: Accept Markdown (`.md`), plain text (`.txt`), Word (`.docx`), and
  HTML (`.html`) as input, via file upload or pasted text.
- FR-2: For any accepted input, produce a `Document` made of typed `Block`s
  (`heading`, `paragraph`, `list`, `quote`, `code`, `callout`, `warning`,
  `timeline_event`, `entity`, `relationship`, `definition`, `reference`,
  `table`, `divider`) grouped into `Section`s.
- FR-3: Plain, unstructured text (no Markdown headers) must still be parsed
  into a reasonable block structure via heuristics (line length, blank-line
  isolation, punctuation patterns) rather than becoming one giant paragraph.
- FR-4: Every accepted input format must yield a `raw_content` (a plain-text
  or reconstructed-markdown representation of the source) so the document can
  be re-edited or re-previewed later, even for formats like `.docx` that have
  no native plain-text form.

### 2.2 Structure & classification

- FR-5: Detect the document's project type — Story Bible, Research Notes,
  Project Plan, Worldbuilding Document, Knowledge Base, Debate Preparation,
  Study Notes, Competition Planning, or Document (unknown) — from keyword
  signals, including multi-word and hyphenated signal phrases, and report a
  confidence score.
- FR-6: Reclassify generic paragraphs into more specific block types where
  the content signals it (e.g. "Important: ..." → callout, "Warning: ..." →
  warning, a short capitalized line followed by a colon-led description →
  entity).

### 2.3 Importance scoring

- FR-7: Assign every block an importance score from 0–100, usable by
  renderers to visually emphasize high-importance content (larger/bolder
  text, distinct styling), and by exporters (e.g. "critical blocks" summary
  in the CLI).

### 2.4 Theming & rendering

- FR-8: Ship at least 10 built-in visual themes, each a complete, self
  consistent design system (typography, color, spacing) built on shared CSS
  custom properties so partial overrides don't break the rest of the theme.
- FR-8a: Provide an autonomous design mode (`theme=auto`) that analyzes the
  document's actual content — genre/mood, recurring structural patterns
  (all-caps field labels, pull-quotes, entity density) — and generates a
  bespoke color palette, font pairing, and targeted typographic treatment
  for it, rather than requiring the user to pick from a fixed preset list.
  This must be the default experience; manual presets remain available as a
  secondary, explicit choice.
- FR-9: Support three render modes: `document` (full themed page), `slides`
  (deck layout), `brief` (condensed one-pager).
- FR-10: Suggest themes based on the detected project type.
- FR-11: Support user-supplied custom CSS that layers on top of a selected
  preset theme (or an auto-generated design). Writing only CSS custom-
  property overrides (e.g. `:root { --accent: #e63946; }`) must be
  sufficient to restyle colors and fonts across the whole document — the
  user should not need to redefine every selector from scratch for a simple
  recolor/refont.
- FR-12: Provide a visual theme Designer that edits colors, fonts, spacing,
  and per-element styling, previews against the user's *actual* uploaded
  document content (not fixed sample/placeholder text) when available, and
  can save custom themes (including auto-generated or imported designs) and
  apply them back to the main editor.
- FR-13: Support a selectable icon style for entity/callout/warning markers:
  Unicode symbols (default, dependency-free), Font Awesome (loaded from a
  CDN), or no icons.
- FR-13a: Support importing an already-designed `.docx` or `.html` document
  and extracting its colors/fonts into a savable preset, prioritizing actual
  applied formatting over template boilerplate.

### 2.5 Export

- FR-14: Export the rendered document to HTML, PDF, DOCX, and PPTX.
- FR-15: DOCX export must render actual tables (not raw pipe-delimited
  markdown text dumped as a paragraph) for `table` blocks.
- FR-16: PPTX export must support procedurally generated themed illustrations
  per slide/topic, and must not silently fail — if a visual can't be
  generated, that should be visible/loggable, not swallowed into an empty
  image.
- FR-16a: Provide an optional page-decoration system (top/bottom margin
  ornament, page border, and content-aware margin doodles) that a user can
  toggle on. The margin ornament and border must render consistently across
  every export format that has a concept of a page or slide (HTML, PDF,
  DOCX, PPTX) using one shared style-selection/motif source rather than a
  per-exporter reimplementation. Margin doodles (per-paragraph contextual
  icons) are HTML/WeasyPrint-PDF-only, since fixed-size slide layouts and
  flowing DOCX text don't have an equivalent stable "margin" concept.

### 2.6 Interfaces

- FR-17: Provide a CLI (`ias.py`) with `transform`, `serve`, and `themes`
  subcommands. The `--theme` choices exposed by the CLI must always match the
  full, current set of registered themes (no drift between the CLI's
  hardcoded list and what the app actually supports).
- FR-18: Provide a web app (Flask) with a live-preview editor and a REST API
  (`/api/transform`, `/api/upload`, `/api/rerender`, `/api/export/*`) for
  programmatic use.

## 3. Non-functional requirements

- NFR-1 (Security): User-supplied filenames used to construct server-side
  file paths (exports) must be sanitized; no request may cause a file to be
  read from or written to a path outside the intended directory.
- NFR-2 (Robustness): A failure in one optional feature (e.g. a single
  procedurally generated visual) must not silently degrade output without
  any signal, and must not crash the whole export.
- NFR-3 (Consistency): The set of themes/options presented to the user must
  be identical whether accessed via CLI or web app.
- NFR-4 (Dependencies): All imports used by the codebase must be declared in
  `requirements.txt`; the codebase must not rely on transitively-installed
  packages that aren't explicitly required.
- NFR-5 (Maintainability): No dead code (unused imports, unreachable
  variables, orphaned regexes) should accumulate in modules that are
  actively maintained.

## 4. Out of scope (for now)

- Real-time multi-user collaborative editing.
- Authentication / per-user accounts (the app is single-user/local by
  design).
- Automatic translation or multi-language content generation.
- Cloud storage integrations (Google Drive, Dropbox, etc.).
