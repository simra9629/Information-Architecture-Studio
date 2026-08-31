"""
Theme Extractor — pull colors and fonts out of an already-designed document
(.docx or .html) so they can be turned into a reusable IAS theme preset,
instead of the user having to rebuild the look by hand in the Designer.

Output shape matches what the Designer/theme_engine already expect:
  properties: {color_bg, color_text, color_accent, color_entity,
               color_callout, color_warning, color_border,
               font_heading, font_body, font_mono,
               base_font_size, line_height, border_radius, body_max_width}
  elements:   {h1: {fg,bg}, h2: {...}, h3, body, entity, callout,
               warning, timeline, quote, th, code}
"""

import re
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

_DEFAULT_PROPERTIES = {
    "color_bg": "#FFFFFF",
    "color_text": "#111111",
    "color_accent": "#3B5BDB",
    "color_entity": "#5C3BC9",
    "color_callout": "#1A6E4A",
    "color_warning": "#C0392B",
    "color_border": "#E0E0E0",
    "font_heading": "Inter",
    "font_body": "Inter",
    "font_mono": "monospace",
    "base_font_size": "16px",
    "line_height": "1.7",
    "border_radius": "6px",
    "body_max_width": "840px",
}

_HEX_RE = re.compile(r'#([0-9A-Fa-f]{6}|[0-9A-Fa-f]{3})\b')


def _norm_hex(h: str) -> str:
    h = h.strip()
    if not h.startswith("#"):
        h = "#" + h
    if len(h) == 4:  # #abc -> #aabbcc
        h = "#" + "".join(c * 2 for c in h[1:])
    return h.upper()


def _is_grayscale(hexcolor: str) -> bool:
    """True for near-black/white/gray colors — not useful as an 'accent'."""
    try:
        h = hexcolor.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return max(r, g, b) - min(r, g, b) < 18
    except Exception:
        return True


def _empty_elements() -> dict:
    return {k: {"fg": None, "bg": None} for k in
            ("h1", "h2", "h3", "body", "entity", "callout",
             "warning", "timeline", "quote", "th", "code")}


# ── HTML extraction ─────────────────────────────────────────────────────

def extract_from_html(html_text: str) -> dict:
    """Extract colors/fonts from an HTML document's <style> rules and,
    failing that, from inline style="" attributes (common in HTML exported
    from Word/Google Docs, which style per-span rather than via a stylesheet).
    """
    from bs4 import BeautifulSoup

    props = dict(_DEFAULT_PROPERTIES)
    elements = _empty_elements()

    soup = BeautifulSoup(html_text, "lxml")

    # 1. Pull rules out of any <style> blocks: "selector { decl: val; ... }"
    style_text = "\n".join(s.get_text() for s in soup.find_all("style"))
    rules = {}
    for m in re.finditer(r'([^{}]+)\{([^{}]+)\}', style_text):
        selector = m.group(1).strip().lower()
        body = m.group(2)
        decl = {}
        for dm in re.finditer(r'([\w-]+)\s*:\s*([^;]+)', body):
            decl[dm.group(1).strip().lower()] = dm.group(2).strip()
        for sel in [s.strip() for s in selector.split(",")]:
            rules.setdefault(sel, {}).update(decl)

    def _color_of(decl: dict, *keys):
        for k in keys:
            v = decl.get(k, "")
            m = _HEX_RE.search(v)
            if m:
                return _norm_hex(m.group(0))
        return None

    def _font_of(decl: dict):
        v = decl.get("font-family", "")
        if not v:
            return None
        first = v.split(",")[0].strip().strip("'\"")
        return first or None

    body_decl = rules.get("body", {}) or rules.get("html", {})
    if body_decl:
        bg = _color_of(body_decl, "background", "background-color")
        text = _color_of(body_decl, "color")
        font = _font_of(body_decl)
        if bg: props["color_bg"] = bg
        if text: props["color_text"] = text
        if font: props["font_body"] = font

    h1_decl = rules.get("h1", {})
    accent = _color_of(h1_decl, "color", "border-bottom-color", "border-bottom", "border-color", "border")
    h1_font = _font_of(h1_decl)
    if accent and not _is_grayscale(accent):
        props["color_accent"] = accent
        elements["h1"]["fg"] = accent
    if h1_font:
        props["font_heading"] = h1_font

    for key, selectors in {
        "entity": [".entity", ".entity-card"],
        "callout": [".callout"],
        "warning": [".warning"],
        "timeline": [".timeline", ".timeline-event"],
        "quote": ["blockquote"],
        "th": ["th"],
    }.items():
        for sel in selectors:
            decl = rules.get(sel)
            if not decl:
                continue
            fg = _color_of(decl, "color", "border-left-color", "border-left", "border-color", "border")
            bg = _color_of(decl, "background", "background-color")
            if fg:
                elements[key]["fg"] = fg
                if key in ("entity", "callout", "warning"):
                    prop_key = {"entity": "color_entity", "callout": "color_callout",
                                "warning": "color_warning"}[key]
                    # If fg is just plain white/black text (e.g. a colored
                    # badge/pill), the bg carries the actual brand color
                    if _is_grayscale(fg) and bg and not _is_grayscale(bg):
                        props[prop_key] = bg
                    else:
                        props[prop_key] = fg
            if bg:
                elements[key]["bg"] = bg
            break

    code_decl = rules.get("code", {}) or rules.get("pre", {})
    code_font = _font_of(code_decl)
    if code_font:
        props["font_mono"] = code_font

    border_decl = rules.get("hr", {}) or rules.get("td", {})
    border = _color_of(border_decl, "border-color", "border-top-color", "border-bottom-color", "border-top", "border-bottom", "border")
    if border:
        props["color_border"] = border

    # 2. Fallback: no <style> block usable — scan inline style="" attributes,
    # bucketing by tag and voting for the most common value per bucket. This
    # mirrors the <style>-block path above, populating both `props` *and*
    # `elements` (previously only `props` was filled here, so an imported
    # doc with no <style> block — the common case for HTML exported from
    # Word/Google Docs — always came back with every element fg/bg null).
    if not rules:
        bg_votes, text_votes, heading_votes, font_votes = Counter(), Counter(), Counter(), Counter()
        # Per-tag-name votes, so h1/h2/h3/blockquote/th/code each keep their
        # own identity instead of being blended into one "heading" bucket.
        tag_fg_votes = {k: Counter() for k in ("h1", "h2", "h3", "blockquote", "th", "code", "pre")}
        tag_bg_votes = {k: Counter() for k in ("h1", "h2", "h3", "blockquote", "th", "code", "pre")}
        class_fg_votes = {"entity": Counter(), "callout": Counter(), "warning": Counter(), "timeline": Counter()}
        class_bg_votes = {"entity": Counter(), "callout": Counter(), "warning": Counter(), "timeline": Counter()}

        for tag in soup.find_all(style=True):
            style_attr = tag.get("style", "")
            decl = {}
            for dm in re.finditer(r'([\w-]+)\s*:\s*([^;]+)', style_attr):
                decl[dm.group(1).strip().lower()] = dm.group(2).strip()
            col = _color_of(decl, "color")
            bg = _color_of(decl, "background", "background-color")
            font = _font_of(decl)
            name = tag.name.lower()
            if name in ("h1", "h2", "h3", "strong", "b") and col and not _is_grayscale(col):
                heading_votes[col] += 1
            elif col:
                text_votes[col] += 1
            if bg:
                bg_votes[bg] += 1
            if font:
                font_votes[font] += 1

            if name in tag_fg_votes:
                if col:
                    tag_fg_votes[name][col] += 1
                if bg:
                    tag_bg_votes[name][bg] += 1

            classes = " ".join(tag.get("class") or []).lower()
            for key in class_fg_votes:
                if key in classes:
                    if col:
                        class_fg_votes[key][col] += 1
                    if bg:
                        class_bg_votes[key][bg] += 1

        if heading_votes:
            props["color_accent"] = heading_votes.most_common(1)[0][0]
        if text_votes:
            props["color_text"] = text_votes.most_common(1)[0][0]
        if bg_votes:
            props["color_bg"] = bg_votes.most_common(1)[0][0]
        if font_votes:
            top_font = font_votes.most_common(1)[0][0]
            props["font_body"] = top_font
            props["font_heading"] = top_font

        for tag_name, elem_key in (("h1", "h1"), ("h2", "h2"), ("h3", "h3"),
                                    ("blockquote", "quote"), ("th", "th"), ("code", "code")):
            if tag_fg_votes[tag_name]:
                elements[elem_key]["fg"] = tag_fg_votes[tag_name].most_common(1)[0][0]
            if tag_bg_votes[tag_name]:
                elements[elem_key]["bg"] = tag_bg_votes[tag_name].most_common(1)[0][0]
        # "code" falls back to <pre> styling if no <code> tags carried one
        if elements["code"]["fg"] is None and tag_fg_votes["pre"]:
            elements["code"]["fg"] = tag_fg_votes["pre"].most_common(1)[0][0]
        if elements["code"]["bg"] is None and tag_bg_votes["pre"]:
            elements["code"]["bg"] = tag_bg_votes["pre"].most_common(1)[0][0]

        for key in ("entity", "callout", "warning", "timeline"):
            fg = class_fg_votes[key].most_common(1)[0][0] if class_fg_votes[key] else None
            bg = class_bg_votes[key].most_common(1)[0][0] if class_bg_votes[key] else None
            if fg:
                elements[key]["fg"] = fg
                if key in ("entity", "callout", "warning"):
                    prop_key = {"entity": "color_entity", "callout": "color_callout",
                                "warning": "color_warning"}[key]
                    if _is_grayscale(fg) and bg and not _is_grayscale(bg):
                        props[prop_key] = bg
                    else:
                        props[prop_key] = fg
            if bg:
                elements[key]["bg"] = bg

        if elements["body"]["fg"] is None and text_votes:
            elements["body"]["fg"] = text_votes.most_common(1)[0][0]

    return {"properties": props, "elements": elements}


# ── DOCX extraction ─────────────────────────────────────────────────────

_DRAWINGML_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def _read_theme_colors_and_fonts(path: str):
    """Read word/theme/theme1.xml for the document's color/font scheme."""
    colors, fonts = {}, {}
    try:
        with zipfile.ZipFile(path) as z:
            theme_names = [n for n in z.namelist() if n.startswith("word/theme/")]
            if not theme_names:
                return colors, fonts
            root = ET.fromstring(z.read(theme_names[0]))
        clr_scheme = root.find(".//a:clrScheme", _DRAWINGML_NS)
        if clr_scheme is not None:
            for child in clr_scheme:
                tag = child.tag.split("}")[-1]
                srgb = child.find("a:srgbClr", _DRAWINGML_NS)
                sysclr = child.find("a:sysClr", _DRAWINGML_NS)
                if srgb is not None and srgb.get("val"):
                    colors[tag] = _norm_hex(srgb.get("val"))
                elif sysclr is not None and sysclr.get("lastClr"):
                    colors[tag] = _norm_hex(sysclr.get("lastClr"))
        font_scheme = root.find(".//a:fontScheme", _DRAWINGML_NS)
        if font_scheme is not None:
            major = font_scheme.find(".//a:majorFont/a:latin", _DRAWINGML_NS)
            minor = font_scheme.find(".//a:minorFont/a:latin", _DRAWINGML_NS)
            if major is not None and major.get("typeface"):
                fonts["heading"] = major.get("typeface")
            if minor is not None and minor.get("typeface"):
                fonts["body"] = minor.get("typeface")
    except Exception:
        pass
    return colors, fonts


def extract_from_docx(path: str) -> dict:
    """
    Extract colors/fonts from a .docx. Priority order (highest first):
      1. Direct run-level formatting actually used in the body — this is
         what most people do (select text, pick a color/font) and is the
         strongest signal of real design intent.
      2. Explicit style-level overrides (Heading 1 / Normal), in case the
         style itself was edited rather than individual runs.
      3. The document's theme XML (word/theme/theme1.xml) — only used for
         whatever's still unset, since an untouched Office theme is mostly
         boilerplate, not something the user actually designed.
      4. Sane defaults.
    """
    from docx import Document as DocxDocument

    props = dict(_DEFAULT_PROPERTIES)
    elements = _empty_elements()

    theme_colors, theme_fonts = _read_theme_colors_and_fonts(path)

    try:
        doc = DocxDocument(path)
    except Exception:
        # Not a valid docx — return theme-only / defaults
        if theme_fonts.get("heading"):
            props["font_heading"] = theme_fonts["heading"]
        if theme_fonts.get("body"):
            props["font_body"] = theme_fonts["body"]
        return {"properties": props, "elements": elements}

    # 1. Run-level scan — highest priority, real design intent
    heading_colors, heading_fonts = Counter(), Counter()
    body_colors, body_fonts = Counter(), Counter()
    highlight_colors = Counter()

    for para in doc.paragraphs:
        is_heading = para.style and para.style.name and "heading" in para.style.name.lower()
        is_large_bold = any(
            r.bold and r.font.size and r.font.size.pt >= 14 for r in para.runs
        )
        bucket_heading = is_heading or is_large_bold
        for run in para.runs:
            if run.font.color and run.font.color.rgb:
                hexcolor = _norm_hex(str(run.font.color.rgb))
                if bucket_heading:
                    if not _is_grayscale(hexcolor):
                        heading_colors[hexcolor] += 1
                else:
                    # Body text: gray/black is a legitimate real color choice,
                    # unlike heading/accent colors where we want a "pop" hue
                    body_colors[hexcolor] += 1
            if run.font.name:
                (heading_fonts if bucket_heading else body_fonts)[run.font.name] += 1
            if run.font.highlight_color:
                highlight_colors[str(run.font.highlight_color)] += 1

    if heading_colors:
        top = heading_colors.most_common(1)[0][0]
        props["color_accent"] = top
        elements["h1"]["fg"] = top
    if body_colors:
        props["color_text"] = body_colors.most_common(1)[0][0]
    if heading_fonts:
        props["font_heading"] = heading_fonts.most_common(1)[0][0]
    if body_fonts:
        props["font_body"] = body_fonts.most_common(1)[0][0]

    # Highlighted text is a common way people mark "important" content by
    # hand — use the most common highlight color as a callout background hint
    if highlight_colors:
        _HIGHLIGHT_HEX = {
            "YELLOW": "#FFF3A0", "BRIGHT_GREEN": "#D4F7D4", "TURQUOISE": "#CFF7F0",
            "PINK": "#FCE0EC", "RED": "#FCE0E0", "DARK_BLUE": "#DCE6FA",
            "TEAL": "#D6F5F0", "GREEN": "#DEF2DE", "VIOLET": "#EBE0FA",
        }
        top_name = highlight_colors.most_common(1)[0][0]
        for key, hexcolor in _HIGHLIGHT_HEX.items():
            if key in top_name.upper():
                elements["callout"]["bg"] = hexcolor
                break

    # 2. Style-level overrides — only fill in what run-level scanning missed
    try:
        h1_style = doc.styles["Heading 1"]
        if not heading_colors and h1_style.font.color and h1_style.font.color.rgb:
            hexcolor = _norm_hex(str(h1_style.font.color.rgb))
            if not _is_grayscale(hexcolor):
                props["color_accent"] = hexcolor
                elements["h1"]["fg"] = hexcolor
        if not heading_fonts and h1_style.font.name:
            props["font_heading"] = h1_style.font.name
    except Exception:
        pass

    try:
        normal_style = doc.styles["Normal"]
        if not body_colors and normal_style.font.color and normal_style.font.color.rgb:
            props["color_text"] = _norm_hex(str(normal_style.font.color.rgb))
        if not body_fonts and normal_style.font.name:
            props["font_body"] = normal_style.font.name
    except Exception:
        pass

    # 3. Theme XML — last resort. Deliberately skip accent2/accent3 for
    # entity/callout: on an untouched Office theme those are arbitrary
    # template colors, not something the user actually designed.
    if props["color_accent"] == _DEFAULT_PROPERTIES["color_accent"]:
        accent = theme_colors.get("accent1")
        if accent and not _is_grayscale(accent):
            props["color_accent"] = accent
            elements["h1"]["fg"] = accent
    if props["color_text"] == _DEFAULT_PROPERTIES["color_text"] and theme_colors.get("dk1"):
        props["color_text"] = theme_colors["dk1"]
    if theme_colors.get("lt1") and theme_colors["lt1"] != "#FFFFFF":
        props["color_bg"] = theme_colors["lt1"]

    # Page background color, if the user explicitly set one (word/settings.xml)
    try:
        with zipfile.ZipFile(path) as z:
            if "word/settings.xml" in z.namelist():
                settings_xml = z.read("word/settings.xml").decode("utf-8", errors="ignore")
                m = re.search(r'<w:background[^>]*w:color="([0-9A-Fa-f]{6})"', settings_xml)
                if m:
                    props["color_bg"] = _norm_hex(m.group(1))
    except Exception:
        pass

    return {"properties": props, "elements": elements}
