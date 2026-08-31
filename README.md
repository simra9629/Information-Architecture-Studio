# Information Architecture Studio (IAS)

Turn a plain document — Markdown, plain text, `.docx`, or `.html` — into a
structured, themed, presentation-quality output. IAS parses your content into
typed blocks (headings, entities, callouts, warnings, timelines, tables...),
automatically detects what *kind* of document it is (story bible, research
notes, debate prep, project plan, etc.), scores each block's importance, and
**designs its own look for it** — a bespoke color palette, typography, and
typographic treatment generated from the document's actual content, not
picked from a fixed list of presets — then renders it as a web page, slide
deck, one-page brief, or exported PDF/DOCX/PPTX.

## Quick start

```bash
pip install -r requirements.txt

# Launch the web app (editor + live preview + theme designer)
python ias.py serve
# → open http://localhost:5000

# Or use the CLI directly
python ias.py transform my-notes.md --mode document --out my-notes.html   # --theme defaults to auto
python ias.py themes                 # list all available manual presets too
```

## Auto-Design — the default experience

Rather than asking you to pick a theme, IAS analyzes the document itself and
designs one:

- **Genre/mood detection** — scores the text against per-genre keyword
  lexicons (22 fiction families, 23 non-fiction registers covering every
  category from academic to finance to technical documentation) and picks
  a dominant mood, or blends two into a genuine hybrid when they're close
  (e.g. "fantasy_epic + dark_mystery").
- **Subgenre/aesthetic modifiers** — 24 of them: cozy, grimdark,
  noblebright, noir, dark/light academia, cottagecore, goblincore,
  fairycore, royalcore, angelcore, dreamcore, weirdcore, liminal, kidcore,
  cybercore, solarpunk, hopepunk, cyberpunk aesthetic, y2k futurism,
  retrofuturism, YA voice, gamified/LitRPG, and epistolary/found-document —
  all layer onto whatever base genre was detected (e.g. "dark_mystery
  [cozy]" for a Cozy Mystery, "crime [noir]" for Noir Crime, "fantasy_epic
  [ya]" for YA Fantasy) — this is what makes hundreds of named subgenres
  and hybrids work without a hand-tuned config for every single one.
- **Food/recipe moods** — recipes don't really have "genres," so instead
  IAS detects food content and classifies it against 23 mood categories
  (Comforting & Cozy, Rich & Indulgent, Bold & Fiery, Elegant &
  Sophisticated, Dark & Mysterious, Celebratory, ...), each with its own
  palette and typography, picked from both cooking-mechanics vocabulary
  and mood/menu-blurb language.
- **Procedural palette generation** — builds a cohesive, genuinely varied
  color palette from a mood-driven base hue using HSL math, with
  per-document jitter so two documents in the same genre don't render
  identically, instead of looking up a fixed preset color scheme.
- **Content-specific typographic treatment** — detects patterns unique to
  *this* document and styles them: recurring all-caps field labels (like a
  character dossier's "CORE IDENTITY", "FATAL FLAW") get tracked-uppercase,
  small-caps, or pill treatment depending on mood; recurring pull-quotes
  (character-voice lines, epigraphs) get a distinct centered/italic
  treatment; entity-heavy documents (story bibles, cast lists) get stronger
  visual separation between entries.
- Works across HTML (document/slides/brief), PDF, and PPTX export — PPTX
  gets its own palette adapter since it renders through python-pptx rather
  than CSS.

## Page decorations & margin doodles

Optional, off by default (toggle "Decorate pages" in the sidebar):

- **Top/bottom margin ornament** — a short rule-glyph-rule motif (e.g.
  `─── ✦ ───`) drawn identically across every output format: CSS in the
  HTML/live preview, a repeating ReportLab canvas callback in the PDF
  fallback, native `w:pgBorders`/header/footer OOXML in DOCX, and a small
  corner text box in PPTX. 35 curated glyph sets span moods from spooky and
  nautical to academic and celestial. Style selection is automatic
  ("Smart") — it scans the document's title/opening content for mood
  keywords, falls back to the detected project type, then to a
  content-hashed varied pool, so results feel intentional rather than
  either always-the-same or literally random.
- **Page border** — an optional matching double-line border, independent
  toggle from the ornament.
- **Margin doodles** (HTML/PDF-via-WeasyPrint only) — small icons scattered
  in the page margins next to the passages that mention them (a `bird`
  icon next to a paragraph about an owl, an `anchor` next to a voyage
  scene, ...). Built on a curated 96-icon subset of the Lucide icon set
  (`app/renderer/doodle_icons/`, ISC license) covering ~340 keywords, with
  a 0–4 density slider from "margin ornament only" to "several doodles per
  paragraph." Icons are inlined as SVG with `stroke="currentColor"`, so
  they automatically pick up the active theme's accent color.

Auto-Design output can be saved as a reusable preset afterward (see below),
so a good result isn't a one-off — you can apply it to future documents too.

### Auto-design package layout — built to scale

`app/themes/auto_designer/` is organized so that adding a new genre,
subgenre, or food mood is just adding one small file — nothing else needs
to change:

```
auto_designer/
  engine.py            Orchestrates detection, blending, modifiers, CSS generation
  palette.py            HSL color math, hue blending, dark/light decision
  decor.py               Structural CSS treatments (glows, dividers, grid lines, ...)
  labels.py                Field-label and pull-quote detection
  blending.py                Hybrid genre blending (circular hue mean, font/decor mixing)
  registry.py                  Auto-discovers every file in a folder or nested folder tree
  fiction/
    adventure/          _base.py (general Adventure) + treasure_hunt.py, expedition.py, ...
    fantasy/             _base.py + grimdark.py, cozy_fantasy.py, urban_fantasy.py, ...
    science_fiction/      _base.py + cyberpunk.py, solarpunk.py, space_opera.py, ...
    horror/ mystery/ thriller/ crime/ drama/ romance/ comedy/ historical/
    literary/ ya/ childrens/ speculative/ dystopian_utopian/ post_apocalyptic/
    slice_of_life/ supernatural/ survival/ western/ war/
                        (22 genre folders total, each with a _base.py + subgenre files)
  nonfiction/
    academic_educational/ business_corporate/ technology_engineering/ science/
    history/ biography_memoir/ journalism/ travel/ self_help/ health_medicine/
    lifestyle/ law_government/ finance_economics/ philosophy_religion/
    arts_culture/ nature_environment/ reference/ technical_communication/
    creative_nonfiction/ educational_resources/ digital_online_content/
    design_product/ planning_management/
                        (23 category folders, same _base.py + subgenre pattern)
  modifiers/              Cross-cutting aesthetic/subgenre flavors (cozy.py, grim.py, noir.py, ...)
  food/                     23 recipe moods (rich_indulgent.py, bold_fiery.py, ...)
```

Each genre folder is its own subpackage: `_base.py` holds that genre's
general config (used when the text matches the broad category but no
specific subgenre), and every other file is a named subgenre with its own
precise signal words and design. For example, Sci-Fi's Cyberpunk and
Solarpunk are **not** the same "punk" modifier with a color tweak — they're
two separate files with genuinely opposite palettes and energy, because
they're genuinely opposite aesthetics:

```python
# fiction/science_fiction/cyberpunk.py — dark, neon, high-saturation
CONFIG = {
    "signals": ["neon-lit", "cyberpunk", "megacity", "chrome and neon", ...],
    "hue": 288, "sat": 0.72, "energy": 0.62,
    "heading_font": "Space Grotesk", "body_font": "IBM Plex Sans", "mono_font": "IBM Plex Mono",
    "label_style": "tracked_upper", "decor": "grid_lines",
}

# fiction/science_fiction/solarpunk.py — bright, green, low-energy
CONFIG = {
    "signals": ["solarpunk", "solar panels bloomed", "renewable energy", ...],
    "hue": 96, "sat": 0.55, "energy": 0.2,
    "heading_font": "Space Grotesk", "body_font": "Karla", "mono_font": "DM Mono",
    "label_style": "small_caps", "decor": "ornament_divider",
}
```

Detection pools every genre's `_base` and every subgenre together (~230+
entries across fiction/nonfiction), scores the document's text against all
of them, and either picks a clear winner, blends two close scorers into a
genuine hybrid (colors blend via circular hue mean; typography and
decoration pull from both — this works across parent genres too, e.g. a
heist story can land on "heist (action) + heist_crime (crime)"), or falls
back to a genre's general `_base` when no specific subgenre stands out.
Cross-cutting aesthetic modifiers (cozy, grimdark, noir, dark academia,
cottagecore, Y2K, ...) still layer on top of whatever was resolved — but
only when the resolved genre/subgenre doesn't already encode that same
flavor (so "fantasy/grimdark" doesn't also get a redundant "[grim]" tag).

## Manual themes & Custom CSS

The 14 hand-built presets (academic, magazine, codex, corporate, detective,
cyberpunk, museum, research, noir, newspaper, scientific, minimalist,
startup, manuscript) are still available for when you want direct control —
toggle "Manual Themes" in the sidebar. Each is a full CSS design system
built on shared CSS custom properties (`--accent`, `--bg`, `--text`,
`--font-heading`, `--font-body`, ...), which is what makes the **Custom
CSS** override box work — write just `:root { --accent: #e63946; }` and the
rest of the theme still holds together, or write full CSS rules (including
things like blurs, `::before` content, custom classes) for complete control.

The Custom CSS box has a collapsible **"Variables you can override"**
reference underneath it — chips showing every override-able variable at its
*current* resolved value (the active preset's own colors/fonts, or the live
auto-design result for whatever's currently loaded). Clicking one inserts a
ready-to-edit `--variable: value;` line at your cursor instead of you
needing to know the variable names or dig the current color out of
DevTools.

## Import a Designed Doc

Already have a `.docx` or `.html` document styled the way you like? Upload
it in the **Import a Designed Doc** panel and IAS extracts its colors and
fonts — prioritizing actual direct formatting (the colors/fonts you
selected by hand) over template boilerplate. If you have a document loaded
in the editor, extraction is immediately followed by a live preview — your
actual document, rendered with the extracted design applied, in an isolated
frame right in the panel — so you can judge whether it looks right before
saving it as a reusable preset or refining it further in the Designer.

## Web app

`python ias.py serve` starts a Flask app with two pages:

- **Editor** (`/`) — paste or upload a document, get a live preview with
  Auto-Design applied by default, switch to a manual theme or write custom
  CSS, pick an icon style (Unicode/Font Awesome/none), and export to
  HTML/PDF/DOCX/PPTX.
- **Designer** (`/designer`) — a full visual theme editor: colors, fonts,
  spacing, per-element styling, live preview against your *actual* uploaded
  document (not placeholder text), and a "Save as theme" / "Apply to
  editor" workflow. Can also load in a design extracted via Import.

## CLI

```
ias transform <input> [--theme THEME] [--mode {document,slides,brief}] [--out OUT]
ias serve [--port PORT] [--debug]
ias themes
```

`--theme` defaults to `auto` (the content-aware auto-design engine); it also
accepts any of the 14 built-in presets by name. `--out` accepts `.html`,
`.pdf`, or `.docx` and picks the right exporter based on the extension.

## Project layout

```
ias.py                      CLI entry point
app_server.py                Flask app (web editor + designer + export API)
app/
  pipeline.py                 Orchestrates parse → structure → importance → theme/auto-design → render
  models/document.py          Document/Section/Block/ProjectType data model
  parser/
    markdown_parser.py         Markdown → blocks
    raw_text_analyzer.py       Heuristic parser for unstructured plain text
    docx_parser.py             .docx → blocks
  structure/structure_engine.py   Project-type detection, block reclassification
  importance/importance_engine.py Per-block 0–100 importance scoring
  themes/
    theme_engine.py             Manual theme presets, custom theme storage, suggestions
    auto_designer/              Content-aware autonomous design engine (see above)
    theme_extractor.py         Extracts colors/fonts from an already-designed docx/html
  renderer/
    html_renderer.py            HTML output for document/slides/brief modes
    presentation_engine.py     .pptx generation
    visual_generator.py        Procedural themed illustrations (matplotlib)
    decorations.py              Page-margin ornament/border + smart style picker
    doodle_icons.py             Content-aware margin-doodle keyword vocab (Lucide SVGs)
    doodle_icons/                Bundled Lucide SVG icon set (ISC license)
  exporters/
    exporters.py                DOCX export, PDF export wrapper (WeasyPrint)
    pdf_exporter.py            Native PDF export (ReportLab) with charts/visuals
static/
  index.html                   Main editor UI
  designer.html                Visual theme designer
themes/                        Saved custom themes (JSON)
exports/                       Server-side export output directory
```

## Requirements

See `requirements.txt`. Notable ones: Flask (web app), `beautifulsoup4` +
`lxml` (HTML/theme-import parsing; Markdown itself is parsed by a
hand-rolled parser, no external Markdown library needed), `python-docx`
(DOCX in/out), `pillow` (image normalization/re-encoding for embedded
images across all input formats), `weasyprint` (PDF via HTML — this is
what gives custom CSS and auto-design full fidelity in PDF exports),
`reportlab` (native PDF fallback), `python-pptx` (PowerPoint export),
`matplotlib` + `numpy` + `scipy` (procedural themed visuals and charts).

Optional: set `ANTHROPIC_API_KEY` to enable AI captioning/OCR of embedded
images (`anthropic` package, not installed by default — see the comment in
`requirements.txt`). Without it, images still extract and render fine,
just without a generated caption.

See `REQUIREMENTS.md` for the full functional/non-functional requirements
this project is built against.

