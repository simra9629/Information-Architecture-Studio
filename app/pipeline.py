"""
Information Architecture Studio — Core Pipeline
"""
import os
import re
from app.parser.markdown_parser import MarkdownParser, PlainTextParser
from app.parser.docx_parser import DocxParser
from app.parser import pdf_parser
from app.parser.raw_text_analyzer import RawTextAnalyzer
from app.structure.structure_engine import StructureEngine
from app.importance.importance_engine import ImportanceEngine
from app.themes.theme_engine import ThemeEngine
from app.themes import auto_designer
from app.renderer.html_renderer import HTMLRenderer


class Pipeline:
    """
    Orchestrates the full IAS processing pipeline:
    Input → Parser → Structure → Importance → Theme → Renderer → Output
    """

    def __init__(self):
        self.md_parser = MarkdownParser()
        self.txt_parser = PlainTextParser()
        self.docx_parser = DocxParser()
        self.raw_analyzer = RawTextAnalyzer()
        self.structure_engine = StructureEngine()
        self.importance_engine = ImportanceEngine()
        self.theme_engine = ThemeEngine()
        self.renderer = HTMLRenderer()

    def run(self, raw_text: str, theme: str = "auto",
            mode: str = "document", source_name: str = "document",
            custom_css: str = "", icon_style: str = "unicode",
            decorate: bool = False, border: bool = False,
            decoration_style: str = "auto", doodle_density: int = None) -> dict:
        """
        Full pipeline. Returns dict with document model + rendered HTML.
        mode: 'document' | 'slides' | 'brief'
        """
        # 1. Detect input type and parse
        input_mode = self._detect_input_mode(raw_text)
        if input_mode == "markdown":
            doc = self.md_parser.parse(raw_text, source_name)
        elif input_mode == "raw":
            pseudo_md = self.raw_analyzer.analyze(raw_text)
            doc = self.md_parser.parse(pseudo_md, source_name)
            doc.metadata["input_mode"] = "raw"
            doc.metadata["pseudo_markdown"] = pseudo_md
        else:
            doc = self.txt_parser.parse(raw_text, source_name)

        # 2. Structure
        doc = self.structure_engine.process(doc)

        # 3. Importance
        doc = self.importance_engine.process(doc)

        # 4. Theme — 'auto' analyzes this document's actual content (genre,
        # recurring label patterns, pull-quote usage, entity density) and
        # generates a bespoke palette/typography/CSS for it, instead of
        # picking from the fixed preset list.
        effective_theme, effective_css, auto_profile, design = self._resolve_auto_design(
            doc, theme, custom_css
        )
        doc.theme = effective_theme
        suggestions = self.theme_engine.suggest(doc)

        # 5. Render
        html = self.renderer.render(doc, theme=effective_theme, mode=mode,
                                     custom_css=effective_css, icon_style=icon_style,
                                     decorate=decorate, border=border,
                                     decoration_style=decoration_style, doodle_density=doodle_density)

        if auto_profile is not None:
            html = auto_designer.apply_field_labels(html, design["field_labels"])

        return {
            "document": doc,
            "html": html,
            "raw_content": raw_text,
            "project_type": doc.project_type.value,
            "type_confidence": doc.type_confidence,
            "theme": theme,
            "mode": mode,
            "suggestions": suggestions,
            "block_count": len(doc.all_blocks),
            "blocks": [b.to_dict() for b in doc.all_blocks],
            "input_mode": doc.metadata.get("input_mode", input_mode),
            "auto_design_profile": auto_profile,
            "auto_design_properties": design["properties"] if design else None,
            "auto_design_elements": design["elements"] if design else None,
        }

    def _resolve_auto_design(self, doc, theme: str, custom_css: str):
        """
        If theme == 'auto', analyze `doc` and generate a bespoke design for
        it. Returns (effective_theme, effective_css, profile_or_None, design_or_None).
        For any other theme value, passes through unchanged. Any explicitly
        provided custom_css is layered on top of the auto-generated design
        rather than discarded, so a user can still nudge the result.
        """
        if theme != "auto":
            return theme, custom_css, None, None
        try:
            design = auto_designer.design(doc)
        except Exception:
            # Auto-design is a nice-to-have layer on top of a document the
            # person is actively trying to view/export -- a bug in genre
            # detection or palette generation for one particular document
            # shouldn't take the whole request down. Fall back to a safe,
            # always-available manual preset and let the document still
            # render; log the real cause server-side so it's diagnosable
            # instead of silently hidden.
            import traceback
            traceback.print_exc()
            return "academic", custom_css, None, None
        built_css = self.theme_engine.build_css_from_properties(
            "auto", design["properties"], design["elements"]
        )
        effective_css = built_css + "\n" + design["custom_css"]
        if custom_css:
            effective_css += "\n" + custom_css
        return "custom:", effective_css, design["profile"], design

    def run_from_file(self, filepath: str, theme: str = "auto",
                      mode: str = "document", custom_css: str = "",
                      icon_style: str = "unicode", decorate: bool = False,
                      border: bool = False, decoration_style: str = "auto", doodle_density: int = None) -> dict:
        """Process a file (md, txt, html, docx)."""
        ext = os.path.splitext(filepath)[1].lower()
        source_name = os.path.basename(filepath)

        if ext in (".md", ".markdown", ".txt"):
            with open(filepath, "r", encoding="utf-8") as f:
                raw = f.read()
            return self.run(raw, theme=theme, mode=mode, custom_css=custom_css,
                             icon_style=icon_style, decorate=decorate, border=border,
                             decoration_style=decoration_style, doodle_density=doodle_density, source_name=source_name)

        elif ext in (".docx",):
            doc = self.docx_parser.parse(filepath, source_name=source_name)
            doc = self.structure_engine.process(doc)
            doc = self.importance_engine.process(doc)

            effective_theme, effective_css, auto_profile, design = self._resolve_auto_design(
                doc, theme, custom_css
            )
            doc.theme = effective_theme
            suggestions = self.theme_engine.suggest(doc)
            html = self.renderer.render(doc, theme=effective_theme, mode=mode,
                                         custom_css=effective_css, icon_style=icon_style,
                                         decorate=decorate, border=border,
                                         decoration_style=decoration_style, doodle_density=doodle_density)
            if auto_profile is not None:
                html = auto_designer.apply_field_labels(html, design["field_labels"])

            return {
                "document": doc,
                "html": html,
                "raw_content": self._blocks_to_markdown(doc),
                "project_type": doc.project_type.value,
                "type_confidence": doc.type_confidence,
                "theme": theme,
                "mode": mode,
                "suggestions": suggestions,
                "block_count": len(doc.all_blocks),
                "blocks": [b.to_dict() for b in doc.all_blocks],
                "input_mode": "docx",
                "auto_design_profile": auto_profile,
                "auto_design_properties": design["properties"] if design else None,
                "auto_design_elements": design["elements"] if design else None,
            }

        elif ext == ".html":
            raw = self._strip_html(filepath)
            return self.run(raw, theme=theme, mode=mode, custom_css=custom_css,
                             icon_style=icon_style, decorate=decorate, border=border,
                             decoration_style=decoration_style, doodle_density=doodle_density, source_name=source_name)

        elif ext == ".pdf":
            raw = pdf_parser.extract_text(filepath)
            result = self.run(raw, theme=theme, mode=mode, custom_css=custom_css,
                               icon_style=icon_style, decorate=decorate, border=border,
                               decoration_style=decoration_style, doodle_density=doodle_density, source_name=source_name)
            result["input_mode"] = "pdf"
            return result

        else:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                raw = f.read()
            return self.run(raw, theme=theme, mode=mode, custom_css=custom_css,
                             icon_style=icon_style, decorate=decorate, border=border,
                             decoration_style=decoration_style, doodle_density=doodle_density, source_name=source_name)

    def _detect_input_mode(self, text: str) -> str:
        """Returns 'markdown', 'plain', or 'raw'."""
        md_signals = ["## ", "### ", "**", "```", "> ", "---", "- [", "| "]
        strong_md = sum(1 for s in md_signals if s in text)
        if strong_md >= 2:
            return "markdown"
        h1_count = len(re.findall(r"^# .+", text, re.MULTILINE))
        if strong_md >= 1 or h1_count >= 1:
            return "markdown"
        plain_signals = 0
        for line in text.splitlines():
            s = line.strip()
            if s and s.isupper() and len(s) < 60:
                plain_signals += 1
            if re.match(r"^\d+[.)]\s+", s):
                plain_signals += 1
            if re.match(r"^[-•*]\s+", s):
                plain_signals += 1
        if plain_signals >= 2:
            return "plain"
        return "raw"

    def _strip_html(self, path: str) -> str:
        try:
            from bs4 import BeautifulSoup
            with open(path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f.read(), "lxml")
        except Exception as e:
            raise RuntimeError(f"Could not read HTML: {e}")
        for tag in soup(["script", "style", "head", "nav", "footer"]):
            tag.decompose()
        root = soup.body or soup
        return self._html_node_to_markdown(root).strip()

    def _html_node_to_markdown(self, node) -> str:
        """Walk an HTML document in order, converting block-level elements
        to their markdown equivalent (headings, paragraphs, lists,
        blockquotes, images, dividers) instead of flattening everything to
        plain text. Images keep an external URL or data: URI as-is (both
        work directly in an <img src>); a relative/local path can't be
        resolved from a standalone uploaded HTML file, so it's skipped
        rather than emitting a broken reference."""
        from bs4 import NavigableString, Tag

        lines = []

        def emit(text):
            if text and text.strip():
                lines.append(text.strip())
                lines.append("")

        def inline_text(el) -> str:
            return el.get_text(" ", strip=True)

        def walk(el):
            for child in el.children:
                if isinstance(child, NavigableString):
                    continue
                if not isinstance(child, Tag):
                    continue
                name = child.name.lower()

                if name in ("h1", "h2", "h3", "h4", "h5", "h6"):
                    level = int(name[1])
                    emit(("#" * level) + " " + inline_text(child))
                elif name == "img":
                    src = (child.get("src") or "").strip()
                    alt = (child.get("alt") or "").strip()
                    if src.startswith(("http://", "https://", "data:")):
                        emit(f"![{alt}]({src})")
                elif name == "p":
                    inner_img = child.find("img")
                    if inner_img and not inline_text(child):
                        walk(child)
                    else:
                        emit(inline_text(child))
                elif name == "blockquote":
                    text = inline_text(child)
                    if text:
                        emit("> " + text)
                elif name in ("ul", "ol"):
                    for li in child.find_all("li", recursive=False):
                        emit("- " + inline_text(li))
                elif name == "hr":
                    emit("---")
                elif name == "figcaption":
                    text = inline_text(child)
                    if text:
                        emit(f"*{text}*")
                elif name == "pre":
                    code = child.get_text()
                    if code.strip():
                        lines.append("```")
                        lines.append(code.strip())
                        lines.append("```")
                        lines.append("")
                elif name == "figure":
                    fig_img = child.find("img")
                    fig_cap = child.find("figcaption")
                    if fig_img:
                        src = (fig_img.get("src") or "").strip()
                        alt = (fig_img.get("alt") or "").strip()
                        if src.startswith(("http://", "https://", "data:")):
                            lines.append(f"![{alt}]({src})")
                            cap_text = inline_text(fig_cap) if fig_cap else ""
                            if cap_text:
                                lines.append(f"*{cap_text}*")
                            lines.append("")
                    else:
                        walk(child)
                elif name in ("div", "section", "article", "main", "body", "header"):
                    walk(child)
                # else: skip unrecognized inline/layout wrappers entirely

        walk(node)
        return "\n".join(lines)

    def _blocks_to_markdown(self, doc) -> str:
        """
        Reconstruct a readable markdown-ish version of a parsed Document.
        Used for formats (like .docx) where we don't have the original
        plain-text source, so the editor/designer still has real content
        to show instead of falling back to placeholder sample text.
        """
        from app.models.document import BlockType

        lines = []
        for block in doc.all_blocks:
            content = block.content or ""
            if block.type in (BlockType.HEADING, BlockType.ENTITY):
                level = block.level or 2
                lines.append(f"{'#' * max(1, min(level, 6))} {content}")
            elif block.type == BlockType.QUOTE:
                lines.append(f"> {content}")
            elif block.type == BlockType.CODE:
                lang = block.metadata.get("language", "")
                lines.append(f"```{lang}\n{content}\n```")
            elif block.type == BlockType.DIVIDER:
                lines.append("---")
            elif block.type == BlockType.IMAGE:
                alt = block.metadata.get("alt", "")
                src = block.metadata.get("src") or content
                lines.append(f"![{alt}]({src})")
                caption = block.metadata.get("caption")
                if not caption and content and content != src:
                    # docx_parser convention: content IS the caption
                    caption = content
                if caption:
                    lines.append(f"*{caption}*")
            elif block.type in (BlockType.LIST, BlockType.TABLE):
                # Already stored as raw multi-line markdown-ish text
                lines.append(content)
            else:
                # paragraph, callout, warning, timeline_event, relationship,
                # definition, reference — original inline text is preserved
                # in block.content, so a plain line reproduces it faithfully
                lines.append(content)
            lines.append("")  # blank line between blocks

        return "\n".join(lines).strip()
