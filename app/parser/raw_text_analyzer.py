"""
Raw Text Analyzer
-----------------
Takes completely unformatted plain prose (no Markdown, no headings) and infers
document structure using heuristics:

  - Short ALL-CAPS lines              → headings
  - Short Title-Case lines alone      → headings or entities
  - Colon-terminated short phrases    → section labels / headings
  - Lines starting with a number+dot  → ordered list
  - Lines starting with dash/bullet   → unordered list
  - "Key: value" single-line pairs    → definition or callout
  - Lines with date patterns          → timeline events
  - Repeated sentence openers        → paragraph groups (section boundary)
  - Table-like aligned text           → tables
  - Warning/Important/Note keywords   → callouts / warnings
  - Relationship phrases              → relationship blocks
  - Paragraph breaks (blank lines)    → section separators
  - Very short standalone lines       → potential headings
  - Quoted text ("…" or "…")          → quotes

The analyzer returns a list of (block_type, content, level) tuples that the
MarkdownParser can then consume after pre-processing into pseudo-Markdown.
"""

import re
from typing import List, Tuple


# ── Compiled patterns ──────────────────────────────────────────────────────
RE_ORDERED_LIST   = re.compile(r"^(\d+)[.):]\s+(.+)")
RE_BULLET_LIST    = re.compile(r"^[-•*·→▸▹]\s+(.+)")
RE_COLON_LABEL    = re.compile(r"^([A-Z][A-Za-z\s]{1,35}):\s*(.+)?$")
RE_DATE_LINE      = re.compile(r"^(?:Year\s+\d{3,4}|\d{4}|\w+ \d{1,2},?\s+\d{4})\s*[:\-–]\s*.+", re.IGNORECASE)
RE_WARNING        = re.compile(r"^(?:Warning|Danger|Alert|Caution)\s*[:\-–]\s*(.+)", re.IGNORECASE)
RE_CALLOUT        = re.compile(r"^(?:Note|Important|Critical|Key Rule|Remember|NB)\s*[:\-–]\s*(.+)", re.IGNORECASE)
RE_RELATIONSHIP   = re.compile(r"^(?:Relationship|Allied with|Enemy of|Mentor to|Rival of|Friend of|Partner of|Married to|Sibling of)\s*[:\-–]?\s*(.+)", re.IGNORECASE)
RE_DEFINITION     = re.compile(r"^([A-Z][a-zA-Z\s]{1,30})\s*[:\-–]\s+([A-Z].{10,})")
RE_QUOTE          = re.compile(r'^["\u201c](.+)["\u201d]\s*(?:[-—]\s*(.+))?$')
RE_REFERENCE      = re.compile(r"^(?:See also|Reference|Source|Cf\.|Ibid\.|Op\. cit\.)\s*[:\-]", re.IGNORECASE)

# Lines that are VERY likely headings if short
HEADING_WORDS     = re.compile(r"^(?:Introduction|Overview|Summary|Background|Conclusion|Abstract|"
                                r"Appendix|References|Methods?|Results?|Discussion|Analysis|"
                                r"Part|Chapter|Section|Contents?|Index|Preface|Foreword|"
                                r"Characters?|Locations?|Timeline|Rules?|Notes?|Settings?|"
                                r"Findings?|Recommendations?|Objectives?)\b", re.IGNORECASE)


class RawTextAnalyzer:
    """
    Converts completely unformatted text into annotated pseudo-Markdown
    that the MarkdownParser can then process normally.
    """

    def analyze(self, raw_text: str) -> str:
        """
        Main entry point. Returns pseudo-Markdown string.
        """
        lines = raw_text.splitlines()
        annotated = self._annotate_lines(lines)
        return self._to_markdown(annotated)

    # ── Phase 1: annotate each line ────────────────────────────────────────

    def _annotate_lines(self, lines: List[str]) -> List[Tuple[str, str, int]]:
        """
        Returns list of (tag, content, level) where tag is one of:
        h1, h2, h3, para, list_item, ordered_item, warning, callout,
        relationship, timeline, definition, table_row, quote, reference, blank
        """
        result = []

        # Pre-pass: collect stats to calibrate heuristics
        non_empty = [l.strip() for l in lines if l.strip()]
        avg_len = sum(len(l) for l in non_empty) / max(len(non_empty), 1)
        # "short" = less than 1/3 of average line length (min 15, max 60 chars)
        short_thresh = min(max(int(avg_len * 0.45), 15), 60)

        i = 0
        while i < len(lines):
            raw = lines[i]
            line = raw.strip()

            if not line:
                result.append(("blank", "", 0))
                i += 1
                continue

            tag, content, level = self._classify_line(line, short_thresh, i, lines)
            result.append((tag, content, level))
            i += 1

        # Post-pass: merge consecutive list items, promote isolated shorts to headings
        result = self._post_process(result, short_thresh)
        return result

    def _classify_line(self, line: str, short_thresh: int, idx: int, all_lines: List[str]) -> Tuple[str, str, int]:
        # ── Explicit structural patterns (highest confidence) ──────────────

        if RE_WARNING.match(line):
            return ("warning", line, 0)

        if RE_CALLOUT.match(line):
            return ("callout", line, 0)

        if RE_RELATIONSHIP.match(line):
            return ("relationship", line, 0)

        if RE_DATE_LINE.match(line):
            return ("timeline", line, 0)

        if RE_REFERENCE.match(line):
            return ("reference", line, 0)

        m = RE_QUOTE.match(line)
        if m:
            return ("quote", line, 0)

        m = RE_ORDERED_LIST.match(line)
        if m:
            return ("ordered_item", m.group(2).strip(), 0)

        m = RE_BULLET_LIST.match(line)
        if m:
            return ("list_item", m.group(1).strip(), 0)

        # ── ALL-CAPS line → heading ────────────────────────────────────────
        stripped_plain = re.sub(r"[^a-zA-Z\s]", "", line).strip()
        if stripped_plain and stripped_plain.isupper() and len(line) <= 60 and len(line.split()) <= 8:
            level = 1 if len(line.split()) <= 3 else 2
            return ("h" + str(level), line.title(), level)

        # ── Short colon-label line → heading or definition ─────────────────
        m = RE_COLON_LABEL.match(line)
        if m:
            label = m.group(1).strip()
            rest = (m.group(2) or "").strip()
            label_words = label.split()
            is_heading_word = HEADING_WORDS.match(label)

            if is_heading_word or (len(label_words) <= 4 and not rest):
                # "Characters:" alone → h2
                return ("h2", label, 2)
            elif len(label_words) <= 3 and rest and len(rest) > 15:
                # "Iron: A metal that suppresses magic" → definition
                return ("definition", line, 0)
            elif len(label_words) <= 5 and not rest:
                # Short label alone with colon → h3
                return ("h3", label, 3)

        # ── Short line surrounded by blanks → heading ─────────────────────
        prev_blank = idx == 0 or not all_lines[idx - 1].strip()

        if len(line) <= short_thresh and prev_blank:
            # Title-Case short line → entity or h3
            words = line.split()
            if len(words) <= 5 and all(w[0].isupper() for w in words if w and w[0].isalpha()):
                if len(words) <= 3:
                    return ("h3_entity", line, 3)
                return ("h2", line, 2)

        # ── Known heading keywords alone ───────────────────────────────────
        if HEADING_WORDS.match(line) and len(line.split()) <= 4:
            return ("h2", line, 2)

        # ── Table-like rows ────────────────────────────────────────────────
        if "\t" in line or (re.search(r"  {3,}", line) and len(line.split()) >= 3):
            return ("table_row", line, 0)

        # ── Definition pattern (Term: explanation) ─────────────────────────
        m = RE_DEFINITION.match(line)
        if m and len(m.group(1).split()) <= 3:
            return ("definition", line, 0)

        # ── Default: paragraph ─────────────────────────────────────────────
        return ("para", line, 0)

    # ── Phase 2: post-processing ───────────────────────────────────────────

    def _post_process(self, items: List[Tuple], short_thresh: int) -> List[Tuple]:
        """
        - Merge consecutive same-type list items
        - Promote isolated short paragraphs between blanks to headings
        - Merge broken paragraphs (consecutive para lines with no blank)
        - Convert table rows into a single table block
        """
        result = []
        i = 0

        while i < len(items):
            tag, content, level = items[i]

            # Merge list items
            if tag in ("list_item", "ordered_item"):
                collected = [content]
                list_tag = tag
                j = i + 1
                while j < len(items) and items[j][0] == list_tag:
                    collected.append(items[j][1])
                    j += 1
                result.append(("list", "\n".join(f"- {c}" for c in collected), 0))
                i = j
                continue

            # Merge table rows
            if tag == "table_row":
                rows = [content]
                j = i + 1
                while j < len(items) and items[j][0] == "table_row":
                    rows.append(items[j][1])
                    j += 1
                if len(rows) >= 2:
                    result.append(("table", "\n".join(rows), 0))
                    i = j
                    continue
                # Single row: treat as paragraph
                result.append(("para", content, 0))
                i += 1
                continue

            # Merge consecutive para lines into paragraphs
            if tag == "para":
                lines_collected = [content]
                j = i + 1
                while j < len(items) and items[j][0] == "para":
                    lines_collected.append(items[j][1])
                    j += 1
                result.append(("para", " ".join(lines_collected), 0))
                i = j
                continue

            result.append((tag, content, level))
            i += 1

        return result

    # ── Phase 3: render to pseudo-Markdown ────────────────────────────────

    def _to_markdown(self, items: List[Tuple]) -> str:
        lines = []
        found_h1 = False

        for tag, content, level in items:
            if tag == "blank":
                lines.append("")
            elif tag == "h1":
                lines.append(f"# {content}")
                found_h1 = True
            elif tag == "h2":
                if not found_h1:
                    lines.append(f"# {content}")
                    found_h1 = True
                else:
                    lines.append(f"## {content}")
            elif tag == "h3":
                lines.append(f"### {content}")
            elif tag == "h3_entity":
                lines.append(f"### {content}")
            elif tag in ("warning", "callout", "relationship", "definition", "reference"):
                lines.append(content)
            elif tag == "timeline":
                lines.append(f"- {content}")
            elif tag == "quote":
                lines.append(f"> {content}")
            elif tag == "list":
                lines.append(content)
            elif tag == "table":
                lines.extend(self._format_table(content))
            elif tag == "para":
                # Split out any inline Important/Warning sentences
                lines.extend(self._split_inline_signals(content))
            lines.append("")

        return "\n".join(lines)

    # Split on "... Warning: ..." even without prior period (space + capital keyword)
    _SPLIT_RE2 = re.compile(
        r'\.\s+((?:Important|Critical|Warning|Danger|Note|Key Rule)\s*[:\-])',
        re.IGNORECASE
    )

    def _split_inline_signals(self, text: str) -> List[str]:
        """
        Split a paragraph that contains embedded Important:/Warning: sentences
        into separate lines so the parser can pick them up as callout/warning blocks.
        """
        # Replace ". Warning:" with ".\nWarning:" to create natural splits
        text = self._SPLIT_RE2.sub(r'.\n\1', text)
        parts = [p.strip() for p in text.splitlines() if p.strip()]
        return parts if parts else [text]

    def _format_table(self, raw: str) -> List[str]:
        """Convert tab/multi-space separated rows to pipe-table markdown."""
        rows = raw.strip().splitlines()
        parsed = []
        for row in rows:
            if "\t" in row:
                cells = [c.strip() for c in row.split("\t") if c.strip()]
            else:
                cells = [c.strip() for c in re.split(r"  {2,}", row) if c.strip()]
            if cells:
                parsed.append(cells)

        if not parsed:
            return [raw]

        # Normalize column count
        max_cols = max(len(r) for r in parsed)
        normalized = [r + [""] * (max_cols - len(r)) for r in parsed]

        md = []
        md.append("| " + " | ".join(normalized[0]) + " |")
        md.append("| " + " | ".join(["---"] * max_cols) + " |")
        for row in normalized[1:]:
            md.append("| " + " | ".join(row) + " |")
        return md
