import re
import uuid
from typing import List
from app.models.document import Block, BlockType, Section, Document


class MarkdownParser:
    """Parses Markdown and plain text into structured Block objects."""

    CALLOUT_PATTERNS = [
        (r"^\*\*(?:Important|Critical|Note|Key Rule)\*\*\s*[:\-]?\s*(.+)", BlockType.CALLOUT),
        (r"^\*\*(?:Warning|Danger|Alert)\*\*\s*[:\-]?\s*(.+)", BlockType.WARNING),
        (r"^(?:Important|Critical|Key Rule)\s*[:\-]\s*(.+)", BlockType.CALLOUT),
        (r"^(?:Warning|Danger|Alert)\s*[:\-]\s*(.+)", BlockType.WARNING),
    ]

    RELATIONSHIP_PATTERNS = [
        r"^Relationship\s*[:\-]\s*(.+)",
        r"^(?:Allied with|Enemy of|Mentor to|Rival of|Friend of|Partner of)\s+(.+)",
    ]

    TIMELINE_PATTERNS = [
        r"^[-\*]?\s*(?:Year\s+\d+|\d{4}|\w+ \d+,? \d{4})\s*[:\-]\s*(.+)",
        r"^(?:Year\s+\d+|\d{4})\s*[:\-]\s*(.+)",
    ]

    DEFINITION_PATTERNS = [
        r"^(?:Definition|Term)\s*[:\-]\s*(.+)",
    ]

    # Matches "- [ ] text" / "* [x] text" while preserving leading whitespace
    # (used for indentation-based subtask nesting) — must be applied to the
    # raw, un-stripped line, not the trimmed one used for most other checks.
    _TASK_RE = re.compile(r"^(\s*)[-\*]\s+\[([ xX])\]\s+(.+)$")

    def parse(self, raw_text: str, source_name: str = "document") -> Document:
        doc_id = str(uuid.uuid4())[:8]
        lines = raw_text.strip().splitlines()

        title = self._extract_title(lines)
        blocks = self._parse_lines(lines)
        sections = self._build_sections(blocks)

        doc = Document(
            id=doc_id,
            title=title,
            all_blocks=blocks,
            sections=sections,
            metadata={"source": source_name, "line_count": len(lines)},
        )
        return doc

    _NON_TITLE_HEADINGS = {
        "contents", "table of contents", "copyright", "dedication",
        "acknowledgments", "acknowledgements", "about the author",
        "also by", "praise for",
    }

    def _extract_title(self, lines: List[str]) -> str:
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("# "):
                candidate = stripped[2:].strip()
                if candidate.lower().rstrip(".:") not in self._NON_TITLE_HEADINGS:
                    return candidate
        return "Untitled Document"

    def _parse_lines(self, lines: List[str]) -> List[Block]:
        blocks: List[Block] = []
        i = 0
        block_counter = 0

        def make_id():
            nonlocal block_counter
            block_counter += 1
            return f"b{block_counter:04d}"

        in_list = False
        list_items = []
        in_task = False
        task_roots = []   # list of {"text":.., "checked":.., "subtasks":[...]}
        task_stack = []   # [(indent, node_dict)] — tracks nesting as we go
        in_code = False
        code_lines = []
        code_lang = ""
        in_table = False
        table_rows = []

        while i < len(lines):
            raw = lines[i]
            line = raw.strip()

            # Code blocks
            if line.startswith("```"):
                if not in_code:
                    in_code = True
                    code_lang = line[3:].strip()
                    code_lines = []
                else:
                    in_code = False
                    blocks.append(Block(
                        id=make_id(), type=BlockType.CODE,
                        content="\n".join(code_lines),
                        metadata={"language": code_lang}
                    ))
                i += 1
                continue

            if in_code:
                code_lines.append(raw)
                i += 1
                continue

            # Flush pending task list
            if in_task and not self._TASK_RE.match(raw):
                if task_roots:
                    self._flush_tasks(blocks, task_roots, make_id)
                    task_roots = []
                    task_stack = []
                in_task = False

            # Flush pending list
            if in_list and not (line.startswith("- ") or line.startswith("* ") or
                                re.match(r"^\d+\.", line)):
                if list_items:
                    blocks.append(Block(
                        id=make_id(), type=BlockType.LIST,
                        content="\n".join(list_items)
                    ))
                    list_items = []
                in_list = False

            # Flush pending table
            if in_table and not (line.startswith("|") or line.startswith("|-")):
                if table_rows:
                    blocks.append(Block(
                        id=make_id(), type=BlockType.TABLE,
                        content="\n".join(table_rows)
                    ))
                    table_rows = []
                in_table = False

            # Empty line
            if not line:
                i += 1
                continue

            # Headings
            heading_match = re.match(r"^(#{1,6})\s+(.+)", line)
            if heading_match:
                level = len(heading_match.group(1))
                text = heading_match.group(2).strip()

                # Check if this heading looks like an entity name. Only H3+
                # -- H2 is this app's own convention for a section header
                # (e.g. "## Entities" / "## Characters"), with the actual
                # named entries nested one level deeper as H3. Running this
                # check on H2 too caused section headers like "Entities" or
                # "Data" to themselves get misread as entity cards.
                if level >= 3 and self._looks_like_entity(text):
                    blocks.append(Block(
                        id=make_id(), type=BlockType.ENTITY,
                        content=text, level=level,
                        metadata={"heading_level": level}
                    ))
                else:
                    blocks.append(Block(
                        id=make_id(), type=BlockType.HEADING,
                        content=text, level=level
                    ))
                i += 1
                continue

            # Images — ![alt](src), optionally followed by an *italic caption*
            # line, with or without a blank line in between (both are common)
            img_match = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
            if img_match:
                alt, src = img_match.group(1).strip(), img_match.group(2).strip()
                meta = {"alt": alt, "src": src}
                consumed = 1
                lookahead = i + 1
                if lookahead < len(lines) and not lines[lookahead].strip():
                    lookahead += 1  # skip a single blank line
                if lookahead < len(lines):
                    cap_match = re.match(r"^[*_]([^*_].+?)[*_]$", lines[lookahead].strip())
                    if cap_match:
                        meta["caption"] = cap_match.group(1).strip()
                        consumed = lookahead - i + 1
                blocks.append(Block(id=make_id(), type=BlockType.IMAGE, content=src, metadata=meta))
                i += consumed
                continue

            # Dividers
            if re.match(r"^[-_*]{3,}$", line):
                blocks.append(Block(id=make_id(), type=BlockType.DIVIDER, content=""))
                i += 1
                continue

            # Tables
            if line.startswith("|"):
                in_table = True
                if not re.match(r"^\|[-\s|:]+\|$", line):
                    table_rows.append(line)
                i += 1
                continue

            # Blockquotes
            if line.startswith("> "):
                quote_text = line[2:]
                blocks.append(Block(id=make_id(), type=BlockType.QUOTE, content=quote_text))
                i += 1
                continue

            # Task lists — "- [ ] text" / "- [x] text", nested by indentation
            task_match = self._TASK_RE.match(raw)
            if task_match:
                indent_str, checked_str, text = task_match.groups()
                indent_level = len(indent_str.expandtabs(4)) // 2
                node = {"text": text.strip(), "checked": checked_str.lower() == "x", "subtasks": []}

                while task_stack and task_stack[-1][0] >= indent_level:
                    task_stack.pop()

                if task_stack:
                    task_stack[-1][1]["subtasks"].append(node)
                else:
                    task_roots.append(node)
                task_stack.append((indent_level, node))
                in_task = True
                i += 1
                continue

            # Lists
            if re.match(r"^[-\*]\s+", line) or re.match(r"^\d+\.\s+", line):
                item_text = re.sub(r"^[-\*\d\.]+\s+", "", line)
                list_items.append(item_text)
                in_list = True
                i += 1
                continue

            # Callouts / Warnings
            callout_found = False
            for pattern, btype in self.CALLOUT_PATTERNS:
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    blocks.append(Block(id=make_id(), type=btype, content=m.group(1).strip()))
                    callout_found = True
                    break
            if callout_found:
                i += 1
                continue

            # Relationships
            for pattern in self.RELATIONSHIP_PATTERNS:
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    blocks.append(Block(
                        id=make_id(), type=BlockType.RELATIONSHIP,
                        content=line
                    ))
                    callout_found = True
                    break
            if callout_found:
                i += 1
                continue

            # Timeline events
            for pattern in self.TIMELINE_PATTERNS:
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    blocks.append(Block(
                        id=make_id(), type=BlockType.TIMELINE_EVENT,
                        content=line
                    ))
                    callout_found = True
                    break
            if callout_found:
                i += 1
                continue

            # Definitions
            for pattern in self.DEFINITION_PATTERNS:
                m = re.match(pattern, line, re.IGNORECASE)
                if m:
                    blocks.append(Block(
                        id=make_id(), type=BlockType.DEFINITION,
                        content=line
                    ))
                    callout_found = True
                    break
            if callout_found:
                i += 1
                continue

            # Default: paragraph
            # Try to collect multi-line paragraph
            para_lines = [line]
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    break
                if re.match(r"^#{1,6}\s", next_line):
                    break
                if next_line.startswith(("- ", "* ", "> ", "```", "|")):
                    break
                if re.match(r"^\d+\.\s", next_line):
                    break
                # Stop if next line is a semantic signal (callout/warning/relationship/etc.)
                if re.match(r"^(?:Warning|Danger|Alert|Important|Critical|Note|Key Rule|"
                            r"Relationship|Allied with|Enemy of|Mentor to|"
                            r"Definition|Term|See also|Reference)\s*[:\-]", next_line, re.IGNORECASE):
                    break
                para_lines.append(next_line)
                i += 1

            para_text = " ".join(para_lines)
            blocks.append(Block(id=make_id(), type=BlockType.PARAGRAPH, content=para_text))
            continue

        # Flush remaining
        if task_roots:
            self._flush_tasks(blocks, task_roots, make_id)
        if list_items:
            blocks.append(Block(id=f"b{block_counter+1:04d}", type=BlockType.LIST,
                                content="\n".join(list_items)))
        if table_rows:
            blocks.append(Block(id=f"b{block_counter+2:04d}", type=BlockType.TABLE,
                                content="\n".join(table_rows)))

        return blocks

    def _flush_tasks(self, blocks: List[Block], task_roots: list, make_id) -> None:
        """Turn parsed top-level task nodes into TASK blocks, one per root task,
        with any nested checkboxes carried along in metadata['subtasks']."""
        for root in task_roots:
            blocks.append(Block(
                id=make_id(), type=BlockType.TASK,
                content=root["text"],
                metadata={"checked": root["checked"], "subtasks": root["subtasks"]},
            ))

    def _looks_like_entity(self, text: str) -> bool:
        """Heuristic: proper noun, not too long, no generic section words."""
        generic = {"overview", "introduction", "summary", "background", "notes",
                   "rules", "settings", "world", "timeline", "characters", "locations",
                   "appendix", "references", "conclusion", "chapter", "section",
                   "part", "contents", "index", "tasks", "todo", "to-do", "checklist",
                   "entities", "entity", "data", "results", "methodology", "discussion",
                   "analysis", "findings", "recommendations", "glossary", "resources",
                   "credits", "acknowledgments", "acknowledgements", "dedication",
                   "prologue", "epilogue", "foreword", "afterword", "goals", "objectives",
                   "risks", "assumptions", "constraints", "scope", "definitions",
                   "terminology", "team", "members", "requirements", "features",
                   "roadmap", "milestones", "metrics", "budget", "cast", "plot", "themes",
                   "setting", "worldbuilding", "lore", "factions", "organizations",
                   "items", "equipment", "quests", "media", "gallery", "images",
                   "attachments", "comments", "faq", "faqs", "meta", "misc",
                   "miscellaneous", "other", "general", "details", "description",
                   "specs", "specifications", "abstract", "prerequisites",
                   "installation", "usage", "examples", "license", "changelog",
                   "contributing", "about", "gods", "deities", "factions", "glossary"}
        words = text.lower().split()
        if len(words) > 5:
            return False
        if any(w in generic for w in words):
            return False
        # Looks like a proper name: first letter capitalized
        if text[0].isupper() and len(words) <= 4:
            return True
        return False

    def _build_sections(self, blocks: List[Block]) -> List[Section]:
        """Group blocks into sections based on heading hierarchy."""
        sections = []
        current_section = None
        section_counter = 0

        for block in blocks:
            if block.type == BlockType.HEADING and block.level == 1:
                if current_section:
                    sections.append(current_section)
                section_counter += 1
                current_section = Section(
                    id=f"s{section_counter:03d}",
                    title=block.content,
                    level=1,
                    blocks=[block]
                )
            elif block.type == BlockType.HEADING and block.level == 2:
                if current_section is None:
                    section_counter += 1
                    current_section = Section(id=f"s{section_counter:03d}",
                                              title="Document", level=1)
                section_counter += 1
                sub = Section(id=f"s{section_counter:03d}",
                              title=block.content, level=2, blocks=[block])
                current_section.subsections.append(sub)
            else:
                if current_section is None:
                    section_counter += 1
                    current_section = Section(id=f"s{section_counter:03d}",
                                              title="Document", level=1)
                if current_section.subsections:
                    current_section.subsections[-1].blocks.append(block)
                else:
                    current_section.blocks.append(block)

        if current_section:
            sections.append(current_section)

        return sections


class PlainTextParser(MarkdownParser):
    """Extends MarkdownParser with extra plain-text heuristics."""

    def parse(self, raw_text: str, source_name: str = "document") -> Document:
        # Pre-process: detect and mark up headings by ALL-CAPS lines or short lines
        lines = raw_text.splitlines()
        processed = []
        for line in lines:
            stripped = line.strip()
            if stripped and stripped.isupper() and len(stripped) < 60 and len(stripped.split()) <= 6:
                processed.append(f"## {stripped.title()}")
            else:
                processed.append(line)
        return super().parse("\n".join(processed), source_name)
