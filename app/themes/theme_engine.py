import json
import os
import re
from typing import List, Tuple, Dict, Optional
from app.models.document import Document, ProjectType

THEME_SUGGESTIONS = {
    ProjectType.STORY_BIBLE:    ["codex", "manuscript", "noir"],
    ProjectType.WORLDBUILDING:  ["codex", "noir", "magazine"],
    ProjectType.RESEARCH_NOTES: ["scientific", "academic", "minimalist"],
    ProjectType.PROJECT_PLAN:   ["corporate", "startup", "academic"],
    ProjectType.KNOWLEDGE_BASE: ["academic", "scientific", "minimalist"],
    ProjectType.STUDY_NOTES:    ["academic", "scientific", "newspaper"],
    ProjectType.DEBATE_PREP:    ["corporate", "newspaper", "detective"],
    ProjectType.UNKNOWN:        ["academic", "minimalist", "magazine"],
}

THEME_META = {
    "academic": {
        "name": "Academic",
        "description": "Clean serif typography, formal layout, blue accents",
        "icon": "🎓"
    },
    "magazine": {
        "name": "Magazine",
        "description": "Bold editorial typography, high-contrast with vivid accents",
        "icon": "📰"
    },
    "codex": {
        "name": "Fantasy Codex",
        "description": "Parchment aesthetic, ornate borders, lore-book styling",
        "icon": "📜"
    },
    "corporate": {
        "name": "Corporate",
        "description": "Clean sans-serif, professional card layout, navy palette",
        "icon": "💼"
    },
    "detective": {
        "name": "Detective Case File",
        "description": "Typewriter fonts, evidence cards, pinboard aesthetic",
        "icon": "🔍"
    },
    "cyberpunk": {
        "name": "Cyberpunk Archive",
        "description": "Neon accents, dark terminal, monospace grid",
        "icon": "⚡"
    },
    "museum": {
        "name": "Museum Exhibit",
        "description": "Clean white walls, elegant sans-serif, specimen cards",
        "icon": "🏛️"
    },
    "research": {
        "name": "Research Brief",
        "description": "Dense information layout, data-forward, citation ready",
        "icon": "🔬"
    },
    "noir": {
        "name": "Noir",
        "description": "Dark moody background, gold accents, Playfair Display drama",
        "icon": "🌑"
    },
    "newspaper": {
        "name": "Newspaper",
        "description": "Fraktur masthead, justified columns, old-press feel",
        "icon": "🗞️"
    },
    "scientific": {
        "name": "Scientific",
        "description": "Auto-numbered sections, Source Serif, academic journal style",
        "icon": "🔭"
    },
    "minimalist": {
        "name": "Minimalist",
        "description": "Maximum whitespace, DM Serif Display, nothing unnecessary",
        "icon": "◻️"
    },
    "startup": {
        "name": "Startup",
        "description": "Dark navy, gradient heading, indigo/violet accent system",
        "icon": "🚀"
    },
    "manuscript": {
        "name": "Manuscript",
        "description": "Cormorant Garamond, cream paper, indented paragraphs, literary",
        "icon": "📖"
    },
}

# Designer-mode configurable properties for each built-in theme
THEME_DEFAULTS: Dict[str, dict] = {
    "academic": {
        "font_body": "Source Sans 3",
        "font_heading": "Lora",
        "font_mono": "monospace",
        "color_bg": "#FAFAFA",
        "color_text": "#1A1A2E",
        "color_accent": "#2B4C9B",
        "color_entity": "#5D3A8E",
        "color_callout": "#1A6E4A",
        "color_warning": "#C0392B",
        "color_border": "#D8DCE8",
        "body_max_width": "820px",
        "body_padding": "48px 40px",
        "base_font_size": "16px",
        "line_height": "1.75",
        "border_radius": "4px",
        "custom_css": "",
    },
    "magazine": {
        "font_body": "Inter",
        "font_heading": "Bebas Neue",
        "font_mono": "monospace",
        "color_bg": "#FFFFFF",
        "color_text": "#111111",
        "color_accent": "#E63946",
        "color_entity": "#111111",
        "color_callout": "#2E7D32",
        "color_warning": "#E63946",
        "color_border": "#E0E0E0",
        "body_max_width": "900px",
        "body_padding": "48px 40px",
        "base_font_size": "16px",
        "line_height": "1.7",
        "border_radius": "0px",
        "custom_css": "",
    },
    "codex": {
        "font_body": "Crimson Text",
        "font_heading": "Cinzel",
        "font_mono": "monospace",
        "color_bg": "#F7F0DC",
        "color_text": "#2C1810",
        "color_accent": "#7B4F1E",
        "color_entity": "#7B4F1E",
        "color_callout": "#4A6640",
        "color_warning": "#8B3A1A",
        "color_border": "#C8A96A",
        "body_max_width": "780px",
        "body_padding": "52px 48px",
        "base_font_size": "17px",
        "line_height": "1.8",
        "border_radius": "2px",
        "custom_css": "",
    },
    "corporate": {
        "font_body": "DM Sans",
        "font_heading": "DM Sans",
        "font_mono": "DM Mono",
        "color_bg": "#F8F9FC",
        "color_text": "#1A1A2E",
        "color_accent": "#1E3A5F",
        "color_entity": "#1E3A5F",
        "color_callout": "#1D4ED8",
        "color_warning": "#D97706",
        "color_border": "#E2E8F0",
        "body_max_width": "900px",
        "body_padding": "40px",
        "base_font_size": "15px",
        "line_height": "1.65",
        "border_radius": "6px",
        "custom_css": "",
    },
    "detective": {
        "font_body": "Courier Prime",
        "font_heading": "Oswald",
        "font_mono": "Courier Prime",
        "color_bg": "#C8B99A",
        "color_text": "#1A1008",
        "color_accent": "#8B1A1A",
        "color_entity": "#1A3A6A",
        "color_callout": "#666600",
        "color_warning": "#B22222",
        "color_border": "#8B7355",
        "body_max_width": "820px",
        "body_padding": "48px 44px",
        "base_font_size": "15px",
        "line_height": "1.7",
        "border_radius": "0px",
        "custom_css": "",
    },
    "cyberpunk": {
        "font_body": "Share Tech Mono",
        "font_heading": "Orbitron",
        "font_mono": "Share Tech Mono",
        "color_bg": "#0A0A12",
        "color_text": "#C8D8E8",
        "color_accent": "#00E5FF",
        "color_entity": "#00E5FF",
        "color_callout": "#00E5FF",
        "color_warning": "#FF6600",
        "color_border": "#1E3050",
        "body_max_width": "860px",
        "body_padding": "40px",
        "base_font_size": "14px",
        "line_height": "1.75",
        "border_radius": "0px",
        "custom_css": "",
    },
    "noir": {
        "font_body": "Libre Baskerville",
        "font_heading": "Playfair Display",
        "font_mono": "monospace",
        "color_bg": "#111111",
        "color_text": "#E8E0D4",
        "color_accent": "#C9A96E",
        "color_entity": "#D4B896",
        "color_callout": "#8BAF8E",
        "color_warning": "#C97B6E",
        "color_border": "#2E2A26",
        "body_max_width": "800px",
        "body_padding": "52px 44px",
        "base_font_size": "16px",
        "line_height": "1.8",
        "border_radius": "0px",
        "custom_css": "",
    },
    "newspaper": {
        "font_body": "Libre Baskerville",
        "font_heading": "Libre Baskerville",
        "font_mono": "monospace",
        "color_bg": "#F5F0E8",
        "color_text": "#111111",
        "color_accent": "#8B0000",
        "color_entity": "#111111",
        "color_callout": "#333333",
        "color_warning": "#8B0000",
        "color_border": "#CCCCCC",
        "body_max_width": "860px",
        "body_padding": "40px 44px",
        "base_font_size": "15px",
        "line_height": "1.7",
        "border_radius": "0px",
        "custom_css": "",
    },
    "scientific": {
        "font_body": "Source Serif 4",
        "font_heading": "Source Sans 3",
        "font_mono": "Source Code Pro",
        "color_bg": "#FFFFFF",
        "color_text": "#111827",
        "color_accent": "#1D4ED8",
        "color_entity": "#7C3AED",
        "color_callout": "#065F46",
        "color_warning": "#92400E",
        "color_border": "#E5E7EB",
        "body_max_width": "780px",
        "body_padding": "48px 44px",
        "base_font_size": "16px",
        "line_height": "1.75",
        "border_radius": "4px",
        "custom_css": "",
    },
    "minimalist": {
        "font_body": "Inter",
        "font_heading": "DM Serif Display",
        "font_mono": "monospace",
        "color_bg": "#FFFFFF",
        "color_text": "#0A0A0A",
        "color_accent": "#0A0A0A",
        "color_entity": "#0A0A0A",
        "color_callout": "#666666",
        "color_warning": "#0A0A0A",
        "color_border": "#F0F0F0",
        "body_max_width": "700px",
        "body_padding": "80px 40px",
        "base_font_size": "17px",
        "line_height": "1.8",
        "border_radius": "0px",
        "custom_css": "",
    },
    "startup": {
        "font_body": "Plus Jakarta Sans",
        "font_heading": "Plus Jakarta Sans",
        "font_mono": "Fira Code",
        "color_bg": "#0F172A",
        "color_text": "#F1F5F9",
        "color_accent": "#6366F1",
        "color_entity": "#38BDF8",
        "color_callout": "#34D399",
        "color_warning": "#FB923C",
        "color_border": "#334155",
        "body_max_width": "880px",
        "body_padding": "48px 44px",
        "base_font_size": "15px",
        "line_height": "1.7",
        "border_radius": "8px",
        "custom_css": "",
    },
    "manuscript": {
        "font_body": "Cormorant Garamond",
        "font_heading": "Cormorant SC",
        "font_mono": "monospace",
        "color_bg": "#FAF7F2",
        "color_text": "#1C1610",
        "color_accent": "#5C3D1E",
        "color_entity": "#3D2B0E",
        "color_callout": "#2D4A2D",
        "color_warning": "#5C2D2D",
        "color_border": "#D4C4B0",
        "body_max_width": "720px",
        "body_padding": "72px 60px",
        "base_font_size": "18px",
        "line_height": "1.9",
        "border_radius": "0px",
        "custom_css": "",
    },
}

# Default empty theme for new custom themes
EMPTY_THEME_DEFAULTS = {
    "font_body": "Inter",
    "font_heading": "Inter",
    "font_mono": "monospace",
    "color_bg": "#FFFFFF",
    "color_text": "#111111",
    "color_accent": "#3B5BDB",
    "color_entity": "#5C3BC9",
    "color_callout": "#1A6E4A",
    "color_warning": "#C0392B",
    "color_border": "#E0E0E0",
    "body_max_width": "840px",
    "body_padding": "48px 40px",
    "base_font_size": "16px",
    "line_height": "1.7",
    "border_radius": "6px",
    "custom_css": "",
}


class ThemeEngine:
    def __init__(self, themes_dir: str = None):
        if themes_dir is None:
            themes_dir = os.path.join(os.path.dirname(__file__), "..", "..", "themes")
        self.themes_dir = themes_dir
        os.makedirs(self.themes_dir, exist_ok=True)

    # ── Suggestions ────────────────────────────────────────────────────
    def suggest(self, doc: Document) -> List[Tuple[str, float]]:
        suggestions = THEME_SUGGESTIONS.get(doc.project_type, ["academic", "magazine"])
        base_conf = doc.type_confidence
        result = []
        for i, theme_id in enumerate(suggestions[:3]):
            conf = max(base_conf - i * 15, 20.0)
            result.append((theme_id, conf))
        return result

    # ── Built-in theme info ────────────────────────────────────────────
    def get_all_themes(self) -> dict:
        all_themes = dict(THEME_META)
        # Merge in saved custom themes
        for tid, custom in self._load_all_custom().items():
            all_themes[tid] = {
                "name": custom.get("name", tid),
                "description": custom.get("description", "Custom theme"),
                "icon": custom.get("icon", "🎨"),
                "custom": True,
            }
        return all_themes

    def get_theme_defaults(self, theme_id: str) -> dict:
        """Return designer-editable properties for a theme (built-in or custom)."""
        # Check custom themes first
        custom = self._load_custom(theme_id)
        if custom:
            return custom.get("properties", EMPTY_THEME_DEFAULTS.copy())
        return THEME_DEFAULTS.get(theme_id, EMPTY_THEME_DEFAULTS).copy()

    # ── Custom theme CRUD ─────────────────────────────────────────────
    def save_custom_theme(self, theme_id: str, name: str, description: str,
                          properties: dict, icon: str = "🎨",
                          elements: dict = None) -> dict:
        """Persist a custom theme to disk as JSON, including per-element colors."""
        data = {
            "id": theme_id,
            "name": name,
            "description": description,
            "icon": icon,
            "properties": properties,
        }
        if elements:
            data["elements"] = elements
        path = self._theme_path(theme_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return data

    def delete_custom_theme(self, theme_id: str) -> bool:
        path = self._theme_path(theme_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    def load_custom_theme(self, theme_id: str) -> Optional[dict]:
        return self._load_custom(theme_id)

    def list_custom_themes(self) -> List[dict]:
        return list(self._load_all_custom().values())

    # ── CSS generation from designer properties ───────────────────────
    def build_css_from_properties(self, theme_id: str, props: dict, elements: dict = None) -> str:
        """
        Generate CSS from designer property dict.
        Used for both live preview and final render.
        """
        fb = props.get("font_body", "Inter")
        fh = props.get("font_heading", "Inter")
        fm = props.get("font_mono", "monospace")

        # Build Google Fonts import
        fonts_needed = set()
        for f in [fb, fh]:
            # Known GF fonts only
            known_gf = {
                "Inter", "Outfit", "DM Sans", "Lora", "Playfair Display",
                "Source Sans 3", "Crimson Text", "IM Fell English", "Cinzel",
                "Bebas Neue", "Libre Baskerville", "Special Elite", "Courier Prime",
                "Oswald", "Share Tech Mono", "Rajdhani", "Orbitron", "DM Mono",
                "Merriweather", "Nunito", "Roboto", "Open Sans", "Raleway",
                "Montserrat", "PT Serif", "Georgia", "Fraunces",
            }
            if f in known_gf:
                fonts_needed.add(f.replace(" ", "+"))

        import_line = ""
        if fonts_needed:
            font_params = "&family=".join(
                f"{f}:wght@300;400;500;600;700" for f in sorted(fonts_needed)
            )
            import_line = f"@import url('https://fonts.googleapis.com/css2?family={font_params}&display=swap');"

        bg = props.get("color_bg", "#FFFFFF")
        text = props.get("color_text", "#111")
        accent = props.get("color_accent", "#3B5BDB")
        entity = props.get("color_entity", "#5C3BC9")
        callout_c = props.get("color_callout", "#1A6E4A")
        warning_c = props.get("color_warning", "#C0392B")
        border = props.get("color_border", "#E0E0E0")
        max_w = props.get("body_max_width", "840px")
        padding = props.get("body_padding", "48px 40px")
        font_size = props.get("base_font_size", "16px")
        line_h = props.get("line_height", "1.7")
        radius = props.get("border_radius", "6px")
        custom_extra = props.get("custom_css", "")

        # Derive lightened versions of accent colors
        entity_bg = self._lighten_hex(entity, 0.92)
        callout_bg = self._lighten_hex(callout_c, 0.92)
        warning_bg = self._lighten_hex(warning_c, 0.93)
        accent_light = self._lighten_hex(accent, 0.92)

        css = f"""{import_line}
:root {{
  --accent: {accent};
  --accent-light: {accent_light};
  --entity: {entity};
  --entity-bg: {entity_bg};
  --call: {callout_c};
  --call-bg: {callout_bg};
  --warn: {warning_c};
  --warn-bg: {warning_bg};
  --border: {border};
  --bg: {bg};
  --text: {text};
  --muted: {self._muted_from(text)};
  --font-heading: '{fh}';
  --font-body: '{fb}';
  --font-mono: '{fm}';
}}
body {{
  font-family: var(--font-body), sans-serif;
  background: var(--bg);
  color: var(--text);
  max-width: {max_w};
  margin: 0 auto;
  padding: {padding};
  font-size: {font_size};
  line-height: {line_h};
}}
h1 {{
  font-family: var(--font-heading), serif;
  font-size: 2.3em;
  color: var(--text);
  border-bottom: 2px solid var(--accent);
  padding-bottom: 12px;
  margin-bottom: 8px;
  font-weight: 700;
}}
h2 {{
  font-family: var(--font-heading), serif;
  font-size: 1.5em;
  color: var(--accent);
  margin: 34px 0 12px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--border);
  font-weight: 600;
}}
h3 {{
  font-family: var(--font-heading), serif;
  font-size: 1.2em;
  color: var(--text);
  margin: 22px 0 8px;
  font-weight: 600;
}}
h4 {{
  font-size: 0.95em;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin: 18px 0 6px;
}}
p {{ margin: 0 0 14px; }}
.entity-card {{
  background: var(--entity-bg);
  border-left: 4px solid var(--entity);
  border-radius: {radius};
  padding: 14px 18px;
  margin: 18px 0;
}}
.entity-card .entity-name {{
  font-family: var(--font-heading), serif;
  font-size: 1.1em;
  font-weight: 700;
  color: var(--entity);
  margin-bottom: 4px;
}}
.callout {{
  background: var(--call-bg);
  border-left: 4px solid var(--call);
  border-radius: {radius};
  padding: 12px 16px;
  margin: 16px 0;
}}
.callout::before {{
  content: "ℹ Note";
  font-size: 0.75em;
  font-weight: 700;
  color: var(--call);
  display: block;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
.warning {{
  background: var(--warn-bg);
  border-left: 4px solid var(--warn);
  border-radius: {radius};
  padding: 12px 16px;
  margin: 16px 0;
}}
.warning::before {{
  content: "⚠ Warning";
  font-size: 0.75em;
  font-weight: 700;
  color: var(--warn);
  display: block;
  margin-bottom: 4px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}}
.timeline-event {{
  padding: 8px 0 8px 20px;
  border-left: 3px solid var(--accent);
  margin: 8px 0;
}}
.relationship {{
  font-style: italic;
  color: var(--muted);
  margin: 6px 0 6px 16px;
}}
.definition {{
  background: var(--accent-light);
  padding: 10px 14px;
  border-radius: {radius};
  margin: 12px 0;
}}
blockquote {{
  border-left: 3px solid var(--border);
  padding: 8px 20px;
  margin: 16px 0;
  color: var(--muted);
  font-style: italic;
}}
ul, ol {{ margin: 8px 0 14px 22px; }}
li {{ margin-bottom: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin: 16px 0; }}
th {{
  background: var(--accent-light);
  color: var(--accent);
  font-weight: 700;
  padding: 10px 14px;
  text-align: left;
  border-bottom: 2px solid var(--accent);
}}
td {{ padding: 9px 14px; border-bottom: 1px solid var(--border); }}
code {{
  font-family: var(--font-mono), monospace;
  background: var(--accent-light);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
}}
pre {{
  font-family: var(--font-mono), monospace;
  background: var(--accent-light);
  border: 1px solid var(--border);
  border-radius: {radius};
  padding: 16px;
  overflow-x: auto;
  margin: 16px 0;
}}
hr {{ border: none; border-top: 1px solid var(--border); margin: 30px 0; }}
.doc-meta {{ font-size: 0.85em; color: var(--muted); margin-bottom: 30px; }}
{custom_extra}
{self._elements_css(elements)}
"""
        return css

    def _elements_css(self, elements: dict) -> str:
        """Per-element fg/bg override CSS, matching the Designer's ELS concept."""
        if not elements:
            return ""
        # fg targets just the label/heading part of a block; bg targets the
        # full container. Kept separate so a real accent color on
        # entity/callout/warning (needed so the Designer has something valid
        # to show) doesn't also recolor the body text inside those blocks —
        # only their label, matching what the base template already does.
        fg_selector_map = {
            "h1": "h1", "h2": "h2", "h3": "h3", "body": "body",
            "entity": ".entity-card .entity-name",
            "callout": ".callout::before", "warning": ".warning::before",
            "timeline": ".timeline-event, .timeline",
            "quote": "blockquote", "th": "th", "code": "code, pre",
        }
        bg_selector_map = {
            **fg_selector_map,
            "entity": ".entity-card", "callout": ".callout", "warning": ".warning",
        }
        rules = []
        for key, el in elements.items():
            if not el:
                continue
            fg = el.get("fg")
            bg = el.get("bg")
            if fg and key in fg_selector_map:
                rules.append(f"{fg_selector_map[key]} {{ color: {fg} !important; }}")
            if bg and bg != "auto" and bg != "null" and key in bg_selector_map:
                rules.append(f"{bg_selector_map[key]} {{ background: {bg} !important; }}")
        return "\n".join(rules)

    # ── Internal helpers ──────────────────────────────────────────────
    def _theme_path(self, theme_id: str) -> str:
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", theme_id)
        return os.path.join(self.themes_dir, f"{safe_id}.json")

    def _load_custom(self, theme_id: str) -> Optional[dict]:
        path = self._theme_path(theme_id)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def _load_all_custom(self) -> dict:
        result = {}
        if not os.path.isdir(self.themes_dir):
            return result
        for fname in os.listdir(self.themes_dir):
            if fname.endswith(".json"):
                path = os.path.join(self.themes_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    tid = data.get("id", fname[:-5])
                    result[tid] = data
                except Exception:
                    pass
        return result

    def _lighten_hex(self, hex_color: str, factor: float) -> str:
        """Mix hex_color with white by factor (0=original, 1=white)."""
        try:
            h = hex_color.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            r2 = int(r + (255 - r) * factor)
            g2 = int(g + (255 - g) * factor)
            b2 = int(b + (255 - b) * factor)
            return f"#{r2:02X}{g2:02X}{b2:02X}"
        except Exception:
            return "#F5F5F5"

    def _muted_from(self, text_color: str) -> str:
        """Derive a muted color from the text color."""
        try:
            h = text_color.lstrip("#")
            if len(h) == 3:
                h = "".join(c * 2 for c in h)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            # Move halfway toward mid-gray
            r2 = int(r + (128 - r) * 0.5)
            g2 = int(g + (128 - g) * 0.5)
            b2 = int(b + (128 - b) * 0.5)
            return f"#{r2:02X}{g2:02X}{b2:02X}"
        except Exception:
            return "#666666"
