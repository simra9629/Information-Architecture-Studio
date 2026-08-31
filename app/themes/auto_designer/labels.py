"""
Detects patterns specific to *this* document — recurring all-caps field
labels (character dossiers, spec sheets) and pull-quotes — so styling can
target exactly what's there instead of a hardcoded guess.
"""

import re
from collections import Counter

from app.models.document import BlockType

_LABEL_PATTERN = re.compile(r"^([A-Z][A-Z /'-]{2,28})\s(?=[A-Z][a-z])")


def detect_field_labels(doc) -> list:
    labels = Counter()
    for block in doc.all_blocks:
        if block.type not in (BlockType.PARAGRAPH, BlockType.ENTITY):
            continue
        m = _LABEL_PATTERN.match(block.content.strip())
        if m:
            label = m.group(1).strip()
            if len(label.split()) >= 2 or len(label) >= 5:
                labels[label] += 1
    # Only count as a real pattern if it recurs — one-off isn't a design signal
    return [label for label, count in labels.items() if count >= 2]


def detect_pull_quotes(doc) -> int:
    return sum(1 for b in doc.all_blocks if b.type == BlockType.QUOTE)


def apply_field_labels(html: str, labels: list) -> str:
    """
    Wrap this document's own detected field-label tokens (e.g. "CORE
    IDENTITY", "FATAL FLAW") at the start of a paragraph/entity block in a
    styled span, so the dossier-style label treatment actually shows up —
    without needing a new block type or touching the default parser/renderer
    behavior for documents that don't have this pattern.
    """
    if not labels:
        return html
    # Longest first so "POWERS / ABILITIES" matches before a shorter overlapping label would
    sorted_labels = sorted(set(labels), key=len, reverse=True)
    escaped = [re.escape(l) for l in sorted_labels]
    pattern = re.compile(
        r'(<(?:p|div class="entity-name">)[^>]*>)(' + "|".join(escaped) + r')(\s)'
    )
    return pattern.sub(r'\1<span class="ias-auto-label">\2</span>\3', html)
