"""
PDF Exporter — Pure Python via ReportLab
No system library dependencies (no libobject, no weasyprint).
Renders the Document model directly to a styled PDF.
"""
import re
import io
from app.models.document import Block, BlockType, Document
from app.renderer import decorations

THEME_STYLES = {
    "academic":   {"bg": "FAFAFA", "text": "1A1A2E", "accent": "2B4C9B", "entity": "5D3A8E", "callout": "1A6E4A", "warning": "C0392B", "border": "D8DCE8"},
    "magazine":   {"bg": "FFFFFF", "text": "111111", "accent": "E63946", "entity": "111111", "callout": "2E7D32", "warning": "E63946", "border": "E0E0E0"},
    "codex":      {"bg": "F7F0DC", "text": "2C1810", "accent": "7B4F1E", "entity": "7B4F1E", "callout": "4A6640", "warning": "8B3A1A", "border": "C8A96A"},
    "corporate":  {"bg": "F8F9FC", "text": "1A1A2E", "accent": "1E3A5F", "entity": "1E3A5F", "callout": "1D4ED8", "warning": "D97706", "border": "E2E8F0"},
    "detective":  {"bg": "C8B99A", "text": "1A1008", "accent": "8B1A1A", "entity": "1A3A6A", "callout": "666600", "warning": "B22222", "border": "8B7355"},
    "cyberpunk":  {"bg": "0A0A12", "text": "C8D8E8", "accent": "00E5FF", "entity": "00E5FF", "callout": "00E5FF", "warning": "FF6600", "border": "1E3050"},
    "noir":       {"bg": "111111", "text": "E8E0D4", "accent": "C9A96E", "entity": "D4B896", "callout": "8BAF8E", "warning": "C97B6E", "border": "2E2A26"},
    "startup":    {"bg": "0F172A", "text": "F1F5F9", "accent": "6366F1", "entity": "38BDF8", "callout": "34D399", "warning": "FB923C", "border": "334155"},
    "scientific": {"bg": "FFFFFF", "text": "111827", "accent": "1D4ED8", "entity": "7C3AED", "callout": "065F46", "warning": "92400E", "border": "E5E7EB"},
    "minimalist": {"bg": "FFFFFF", "text": "0A0A0A", "accent": "0A0A0A", "entity": "0A0A0A", "callout": "666666", "warning": "0A0A0A", "border": "F0F0F0"},
    "manuscript": {"bg": "FAF7F2", "text": "1C1610", "accent": "5C3D1E", "entity": "3D2B0E", "callout": "2D4A2D", "warning": "5C2D2D", "border": "D4C4B0"},
    "newspaper":  {"bg": "F5F0E8", "text": "111111", "accent": "8B0000", "entity": "111111", "callout": "333333", "warning": "8B0000", "border": "CCCCCC"},
}


_DECOR_FONT_NAME = "IASDecorFont"
_decor_font_ready = None  # tri-state cache: None = not checked yet


def _decoration_font():
    """Register a Unicode-capable TTF for corner decoration glyphs (the
    reportlab base-14 fonts only support WinAnsi/CP1252, which doesn't
    include any of the star/flourish glyphs used here) and return its
    registered name, or None if no suitable font could be found -- in
    which case callers should fall back to a WinAnsi-safe glyph instead
    of drawing with a font that can't render the requested character."""
    global _decor_font_ready
    if _decor_font_ready is not None:
        return _DECOR_FONT_NAME if _decor_font_ready else None
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:\\Windows\\Fonts\\seguisym.ttf",
    ]
    try:
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        import os as _os
        for path in candidates:
            if _os.path.exists(path):
                pdfmetrics.registerFont(TTFont(_DECOR_FONT_NAME, path))
                _decor_font_ready = True
                return _DECOR_FONT_NAME
    except Exception:
        pass
    _decor_font_ready = False
    return None


def _is_manuscript(doc: Document) -> bool:
    """Prose-heavy documents (novels, narrative nonfiction -- almost entirely
    PARAGRAPH/HEADING blocks with none of the structured-note block types)
    read far better with book typesetting (serif font, indented paragraphs,
    a fresh page per chapter) than with the dense document-style layout
    built for structured notes/bibles with lots of entities/callouts/tables."""
    blocks = doc.all_blocks
    if len(blocks) < 20:
        return False
    prose_types = {BlockType.PARAGRAPH, BlockType.HEADING, BlockType.QUOTE, BlockType.DIVIDER}
    prose_count = sum(1 for b in blocks if b.type in prose_types)
    return prose_count / len(blocks) > 0.9


_SERIF_HINTS = ("serif", "fraunces", "cinzel", "playfair", "lora", "crimson",
                "georgia", "garamond", "baskerville", "merriweather", "times")
_MONO_HINTS = ("mono", "courier", "consolas")


def _classify_font(name: str) -> str:
    """Map a webfont family name to the closest ReportLab base-14 family
    (serif/sans/mono) -- ReportLab can't render arbitrary Google Fonts
    without embedding the actual font files, so this at least picks a
    visually appropriate stand-in instead of always defaulting to
    Helvetica regardless of what the design actually chose."""
    n = (name or "").lower()
    if any(h in n for h in _MONO_HINTS):
        return "mono"
    if any(h in n for h in _SERIF_HINTS):
        return "serif"
    return "sans"


_BASE14 = {
    "serif": ("Times-Roman", "Times-Bold", "Times-Italic"),
    "sans":  ("Helvetica", "Helvetica-Bold", "Helvetica-Oblique"),
    "mono":  ("Courier", "Courier-Bold", "Courier-Oblique"),
}
_ITALIC_FOR = {"Times-Roman": "Times-Italic", "Helvetica": "Helvetica-Oblique",
               "Courier": "Courier-Oblique"}


def export_pdf(doc: Document, theme: str = "academic", palette: dict = None,
                decorate: bool = False, border: bool = False,
                decoration_style: str = "auto") -> bytes:
    """Export Document to PDF bytes using ReportLab.

    If `palette` is given (e.g. from auto_designer.to_docx_palette, whose
    hex values just need the leading '#' stripped), it's used instead of
    the THEME_STYLES lookup -- otherwise an auto-designed or custom theme
    would silently render with the hardcoded 'academic' colors, since
    neither 'auto' nor 'custom:' is a key in THEME_STYLES. `palette` may
    also carry 'heading_font'/'body_font' (webfont family names) -- these
    get mapped to the closest ReportLab base-14 family via _classify_font,
    since ReportLab can't render the actual webfont without it being
    embedded.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                     HRFlowable, PageBreak)
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER

    manuscript = _is_manuscript(doc)

    requested_heading_font = (palette or {}).get("heading_font")
    requested_body_font = (palette or {}).get("body_font")

    pal = THEME_STYLES.get(theme, THEME_STYLES["academic"])
    if palette:
        pal = {**pal, **{k: v.lstrip("#") for k, v in palette.items() if k in pal}}
    tx_c  = colors.HexColor("#" + pal["text"])
    ac_c  = colors.HexColor("#" + pal["accent"])
    en_c  = colors.HexColor("#" + pal["entity"])
    ca_c  = colors.HexColor("#" + pal["callout"])
    wa_c  = colors.HexColor("#" + pal["warning"])
    bo_c  = colors.HexColor("#" + pal["border"])

    buf = io.BytesIO()
    pdoc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=22*mm, rightMargin=22*mm,
        topMargin=24*mm, bottomMargin=24*mm,
        title=doc.title,
    )

    # ── Styles ──────────────────────────────────────────────────────────
    def ps(name, **kw):
        return ParagraphStyle(name, **kw)

    if requested_heading_font or requested_body_font:
        heading_family = _classify_font(requested_heading_font or requested_body_font)
        body_family = _classify_font(requested_body_font or requested_heading_font)
        bold_font, _, _ = _BASE14[heading_family]
        base_font, _, _ = _BASE14[body_family]
        mono_font = _BASE14["mono"][0]
    elif manuscript:
        base_font = "Times-Roman"
        bold_font = "Times-Bold"
        mono_font = "Courier"
    else:
        base_font = "Helvetica"
        bold_font = "Helvetica-Bold"
        mono_font = "Courier"

    if manuscript:
        S = {
            "h1": ps("H1", fontName=bold_font, fontSize=20, textColor=tx_c,
                     spaceAfter=18, spaceBefore=6, leading=24, alignment=TA_CENTER),
            "h2": ps("H2", fontName=bold_font, fontSize=15, textColor=ac_c,
                     spaceAfter=10, spaceBefore=14, leading=19, alignment=TA_CENTER),
            "h3": ps("H3", fontName=bold_font, fontSize=13, textColor=tx_c,
                     spaceAfter=6, spaceBefore=10, leading=17, alignment=TA_CENTER),
            "body": ps("Body", fontName=base_font, fontSize=11.5, textColor=tx_c,
                       spaceAfter=0, leading=18, alignment=TA_JUSTIFY,
                       firstLineIndent=18),
            "meta": ps("Meta", fontName=base_font, fontSize=9, textColor=bo_c,
                       spaceAfter=8, leading=12, alignment=TA_CENTER),
        }
    else:
        S = {
            "h1": ps("H1", fontName=bold_font, fontSize=22, textColor=tx_c,
                     spaceAfter=4, spaceBefore=10, leading=26),
            "h2": ps("H2", fontName=bold_font, fontSize=16, textColor=ac_c,
                     spaceAfter=3, spaceBefore=8, leading=20),
            "h3": ps("H3", fontName=bold_font, fontSize=13, textColor=tx_c,
                     spaceAfter=2, spaceBefore=6, leading=17),
            "body": ps("Body", fontName=base_font, fontSize=11, textColor=tx_c,
                       spaceAfter=5, leading=16, alignment=TA_JUSTIFY),
            "meta": ps("Meta", fontName=base_font, fontSize=9, textColor=bo_c,
                       spaceAfter=8, leading=12),
        }

    S.update({
        "entity": ps("Entity", fontName=bold_font, fontSize=12, textColor=en_c,
                     spaceAfter=3, spaceBefore=4, leading=16),
        "callout": ps("Callout", fontName=base_font, fontSize=11, textColor=ca_c,
                      leftIndent=12, spaceAfter=4, leading=15),
        "warning": ps("Warning", fontName=bold_font, fontSize=11, textColor=wa_c,
                      leftIndent=12, spaceAfter=4, leading=15),
        "quote": ps("Quote", fontName=_ITALIC_FOR.get(base_font, "Helvetica-Oblique"),
                    fontSize=12, textColor=tx_c, leftIndent=16, spaceAfter=5, leading=17),
        "list_item": ps("ListItem", fontName=base_font, fontSize=11, textColor=tx_c,
                        leftIndent=16, spaceAfter=2, leading=15,
                        bulletIndent=8, bulletFontName=base_font),
        "code": ps("Code", fontName=mono_font, fontSize=9, textColor=tx_c,
                   leftIndent=10, spaceAfter=4, leading=13),
        "timeline": ps("Timeline", fontName=base_font, fontSize=11, textColor=ac_c,
                       leftIndent=20, spaceAfter=3, leading=15),
    })

    # ── Build story ──────────────────────────────────────────────────────
    story = []

    # Title
    title_style = ps("TitlePage", fontName=bold_font, fontSize=26, textColor=tx_c,
                      spaceAfter=4, leading=32, alignment=TA_CENTER) if manuscript else S["h1"]
    story.append(Paragraph(_esc(doc.title), title_style))
    if not manuscript:
        story.append(HRFlowable(width="100%", thickness=2, color=ac_c, spaceAfter=4))
    if doc.project_type and doc.project_type.value != "Document" and not manuscript:
        story.append(Paragraph(
            f"{doc.project_type.value} — {len(doc.all_blocks)} blocks",
            S["meta"]
        ))
    story.append(Spacer(1, 3*mm))
    if manuscript:
        story.append(PageBreak())

    first_h1_seen = False
    for block in doc.all_blocks:
        if manuscript and block.type == BlockType.HEADING and block.level == 1:
            if first_h1_seen:
                story.append(PageBreak())
            first_h1_seen = True
        flowables = _block_to_flowables(block, S, ac_c, en_c, ca_c, wa_c, bo_c, tx_c, manuscript)
        story.extend(flowables)

    from reportlab.lib.pagesizes import A4 as _A4

    def _paint_bg(canvas, _doc):
        canvas.saveState()
        canvas.setFillColor(colors.HexColor("#" + pal["bg"]))
        canvas.rect(0, 0, _A4[0], _A4[1], stroke=0, fill=1)
        canvas.restoreState()

        if border:
            canvas.saveState()
            canvas.setStrokeColor(ac_c)
            canvas.setLineWidth(2.2)
            inset = 12 * mm
            canvas.rect(inset, inset, _A4[0] - 2 * inset, _A4[1] - 2 * inset, stroke=1, fill=0)
            canvas.setLineWidth(0.8)
            inner_inset = inset + 2.2 * mm
            canvas.rect(inner_inset, inner_inset, _A4[0] - 2 * inner_inset, _A4[1] - 2 * inner_inset,
                        stroke=1, fill=0)
            canvas.restoreState()

        if decorate:
            resolved_style = decorations.resolve_style(decoration_style, doc, theme)
            primary, secondary = decorations.DECORATION_SETS.get(
                resolved_style, decorations.DECORATION_SETS[decorations.DEFAULT_SET])
            font_name = _decoration_font()
            if font_name:
                top_text = decorations.margin_text(primary)
                bottom_text = decorations.margin_text(secondary)
                draw_font = font_name
            else:
                # Without a Unicode-capable font on this system, the star/
                # rule glyphs aren't in the WinAnsi encoding the base-14
                # fonts support -- fall back to plain ASCII dashes and a
                # WinAnsi-safe bullet instead of missing-glyph boxes.
                top_text = bottom_text = "--- \u2022 ---"
                draw_font = "Helvetica"
            size = 15
            pad_y = 16 * mm
            canvas.saveState()
            canvas.setFillColor(ac_c)
            canvas.setFont(draw_font, size)
            canvas.drawCentredString(_A4[0] / 2, _A4[1] - pad_y, top_text)
            canvas.drawCentredString(_A4[0] / 2, pad_y - size * 0.3, bottom_text)
            canvas.restoreState()

    pdoc.build(story, onFirstPage=_paint_bg, onLaterPages=_paint_bg)
    return buf.getvalue()


def _flatten_task(text: str, checked: bool, subtasks: list, depth: int = 0) -> list:
    """Flatten a task + its nested subtasks into [(text, checked, depth), ...]."""
    out = [(text, checked, depth)]
    for s in subtasks or []:
        out.extend(_flatten_task(s.get("text", ""), bool(s.get("checked")),
                                  s.get("subtasks") or [], depth + 1))
    return out


def _image_flowables(block: Block, S):
    """Build ReportLab flowables for an IMAGE block: the picture itself
    (scaled to fit the page width, never upscaled beyond native size) plus
    a centered italic caption if one is available. Returns [] rather than
    raising if the image can't be decoded/embedded."""
    from reportlab.platypus import Image, Paragraph, Spacer
    from reportlab.lib.units import mm
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.styles import ParagraphStyle
    from app.parser.image_pipeline import from_data_uri, is_data_uri
    import io

    meta = block.metadata or {}
    src = meta.get("src") or block.content or ""
    caption = meta.get("caption") or ""
    if block.content and block.content != src and not caption:
        caption = block.content  # docx_parser convention: content IS the caption

    if not is_data_uri(src):
        return []
    data, _ext = from_data_uri(src)
    if not data:
        return []

    max_width = 166 * mm  # A4 minus the 22mm left/right margins used in export_pdf
    try:
        from PIL import Image as PILImage
        with PILImage.open(io.BytesIO(data)) as im:
            px_w, px_h = im.width, im.height
            dpi = im.info.get("dpi", (96, 96))[0] or 96
        native_width = (px_w / dpi) * 72  # points
        native_height = (px_h / dpi) * 72
        if native_width <= max_width:
            w, h = native_width, native_height
        else:
            ratio = max_width / native_width
            w, h = max_width, native_height * ratio
    except Exception:
        w, h = max_width, max_width * 0.6  # reasonable fallback box if PIL/dims unavailable

    try:
        img = Image(io.BytesIO(data), width=w, height=h)
    except Exception:
        return []
    img.hAlign = "CENTER"
    out = [img, Spacer(1, 1 * mm)]

    if caption:
        cap_style = ParagraphStyle(
            "ImageCaption", fontName=S["quote"].fontName, fontSize=9,
            textColor=S["quote"].textColor, alignment=TA_CENTER, leading=12,
        )
        out.append(Paragraph(_esc(caption), cap_style))
        out.append(Spacer(1, 2 * mm))
    return out


def _block_to_flowables(block: Block, S, ac_c, en_c, ca_c, wa_c, bo_c, tx_c, manuscript=False):
    from reportlab.platypus import Paragraph, Spacer, HRFlowable, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    bt = block.type
    if bt == BlockType.IMAGE:
        return _image_flowables(block, S)
    content = _esc(block.content)

    if bt == BlockType.HEADING:
        level = block.level
        style = S["h1"] if level == 1 else S["h2"] if level == 2 else S["h3"]
        if manuscript:
            return [Paragraph(content, style)]
        return [Paragraph(content, style), Spacer(1, 1*mm)]

    elif bt == BlockType.PARAGRAPH:
        if manuscript:
            return [Paragraph(content, S["body"])]
        return [Paragraph(content, S["body"]), Spacer(1, 1*mm)]

    elif bt == BlockType.ENTITY:
        return [
            Paragraph(f"◆  {content}", S["entity"]),
            Spacer(1, 1*mm),
        ]

    elif bt == BlockType.CALLOUT:
        return [
            HRFlowable(width="100%", thickness=0.5, color=ca_c, spaceAfter=2),
            Paragraph("<b>NOTE</b>", S["callout"]),
            Paragraph(content, S["callout"]),
            HRFlowable(width="100%", thickness=0.5, color=ca_c, spaceAfter=3),
            Spacer(1, 1*mm),
        ]

    elif bt == BlockType.WARNING:
        return [
            HRFlowable(width="100%", thickness=1, color=wa_c, spaceAfter=2),
            Paragraph("<b>! WARNING</b>", S["warning"]),
            Paragraph(content, S["warning"]),
            HRFlowable(width="100%", thickness=1, color=wa_c, spaceAfter=3),
            Spacer(1, 1*mm),
        ]

    elif bt == BlockType.QUOTE:
        return [
            Paragraph(f'"{content}"', S["quote"]),
            Spacer(1, 2*mm),
        ]

    elif bt == BlockType.LIST:
        items = [i.lstrip("- ").strip() for i in block.content.split("\n") if i.strip()]
        flowables = []
        for item in items:
            flowables.append(Paragraph(f"•  {_esc(item)}", S["list_item"]))
        flowables.append(Spacer(1, 2*mm))
        return flowables

    elif bt == BlockType.TIMELINE_EVENT:
        return [
            Paragraph(f"→  {content}", S["timeline"]),
            Spacer(1, 1*mm),
        ]

    elif bt == BlockType.TASK:
        from reportlab.lib.styles import ParagraphStyle
        flowables = []
        for text, checked, depth in _flatten_task(block.content, bool(block.metadata.get("checked")),
                                                    block.metadata.get("subtasks") or []):
            box = "[x]" if checked else "[ ]"
            style = ParagraphStyle(
                f"task{depth}", parent=S["list_item"],
                leftIndent=(S["list_item"].leftIndent or 0) + depth * 14,
                textColor=colors.HexColor("#999999") if checked else S["list_item"].textColor,
            )
            line = f"{box}  <strike>{_esc(text)}</strike>" if checked else f"{box}  {_esc(text)}"
            flowables.append(Paragraph(line, style))
        flowables.append(Spacer(1, 2*mm))
        return flowables

    elif bt == BlockType.CODE:
        return [
            Paragraph(content, S["code"]),
            Spacer(1, 2*mm),
        ]

    elif bt == BlockType.TABLE:
        rows = _parse_table_rows(block.content)
        if rows and len(rows) >= 2:
            max_cols = max(len(r) for r in rows)
            rows = [r + [""] * (max_cols - len(r)) for r in rows]
            tbl = Table(rows, hAlign="LEFT")
            style_cmds = [
                ("BACKGROUND", (0,0), (-1,0), ac_c),
                ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
                ("FONTNAME",   (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",   (0,0), (-1,-1), 9),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F5F5F5")]),
                ("GRID",       (0,0), (-1,-1), 0.5, bo_c),
                ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("LEFTPADDING", (0,0), (-1,-1), 6),
            ]
            tbl.setStyle(TableStyle(style_cmds))
            return [tbl, Spacer(1, 3*mm)]
        return []  # degenerate table (0-1 rows) -- nothing sensible to render

    elif bt == BlockType.DIVIDER:
        return [HRFlowable(width="100%", thickness=0.5, color=bo_c, spaceAfter=4, spaceBefore=4)]

    elif bt == BlockType.RELATIONSHIP:
        return [Paragraph(f"<i>{content}</i>", S["body"]), Spacer(1, 1*mm)]

    elif bt == BlockType.DEFINITION:
        return [Paragraph(f"<b>Definition:</b> {content}", S["body"]), Spacer(1, 1*mm)]

    # default
    if block.content.strip():
        return [Paragraph(content, S["body"]), Spacer(1, 1*mm)]
    return []


def _esc(text: str) -> str:
    """Escape for ReportLab paragraph markup."""
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    # Convert **bold** to <b>bold</b>. DOTALL so a span containing an
    # embedded newline (e.g. a manual line break inside a bold run from a
    # Word doc) still matches instead of silently failing and leaving
    # literal ** in the output.
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.DOTALL)
    text = re.sub(r"\*(.+?)\*",     r"<i>\1</i>", text, flags=re.DOTALL)
    return text


def _parse_table_rows(raw: str) -> list:
    rows = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if not line or re.match(r"^\|[-\s|:]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells:
            rows.append(cells)
    return rows
