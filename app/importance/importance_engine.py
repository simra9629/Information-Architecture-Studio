import re
from collections import Counter
from typing import List, Dict
from app.models.document import Block, BlockType, Document


HIGH_IMPORTANCE_KEYWORDS = {
    "important", "critical", "warning", "key rule", "crucial", "essential",
    "must", "never", "always", "required", "forbidden", "prohibited",
    "core", "fundamental", "primary", "main", "central",
}

MEDIUM_IMPORTANCE_KEYWORDS = {
    "note", "remember", "significant", "notable", "relevant", "major",
    "secondary", "key", "special", "unique",
}

# Block type base scores
TYPE_BASE_SCORES: Dict[BlockType, float] = {
    BlockType.WARNING:        85.0,
    BlockType.CALLOUT:        75.0,
    BlockType.ENTITY:         65.0,
    BlockType.TIMELINE_EVENT: 55.0,
    BlockType.RELATIONSHIP:   60.0,
    BlockType.DEFINITION:     50.0,
    BlockType.HEADING:        45.0,
    BlockType.QUOTE:          40.0,
    BlockType.LIST:           35.0,
    BlockType.PARAGRAPH:      25.0,
    BlockType.CODE:           30.0,
    BlockType.TABLE:          45.0,
    BlockType.REFERENCE:      30.0,
    BlockType.IMAGE:          20.0,
    BlockType.DIVIDER:         5.0,
    BlockType.TASK:           40.0,
}


class ImportanceEngine:
    """
    Scores each block 0-100 based on:
    - Type base score
    - Keyword signals
    - Term frequency (repeated concepts matter more)
    - Position (early content scores higher)
    - Heading level proximity
    - Cross-reference count
    """

    def process(self, doc: Document) -> Document:
        blocks = doc.all_blocks
        if not blocks:
            return doc

        # Build term frequency map across full document
        term_freq = self._build_term_frequency(blocks)
        entity_names = {b.content.lower() for b in blocks if b.type == BlockType.ENTITY}
        total_blocks = len(blocks)

        for i, block in enumerate(blocks):
            score = TYPE_BASE_SCORES.get(block.type, 25.0)

            # Keyword boost
            text_lower = block.content.lower()
            kw_boost = 0.0
            for kw in HIGH_IMPORTANCE_KEYWORDS:
                if kw in text_lower:
                    kw_boost += 15.0
                    break
            for kw in MEDIUM_IMPORTANCE_KEYWORDS:
                if kw in text_lower:
                    kw_boost += 7.0
                    break
            score += min(kw_boost, 20.0)

            # Bold importance markers in text
            if re.search(r"\*\*(?:Important|Critical|Warning|Key Rule)\*\*", block.content, re.IGNORECASE):
                score += 18.0

            # Position bonus (first 20% of document)
            position_ratio = i / total_blocks
            if position_ratio < 0.1:
                score += 10.0
            elif position_ratio < 0.2:
                score += 5.0

            # Heading level bonus
            if block.type == BlockType.HEADING:
                score += max(0, (4 - block.level) * 8)

            # Entity cross-reference bonus: how many other blocks mention this entity?
            if block.type == BlockType.ENTITY:
                name = block.content.lower()
                ref_count = term_freq.get(name, 0)
                score += min(ref_count * 5, 25.0)

            # If block mentions a known entity, slight boost
            entity_mentions = sum(1 for name in entity_names if name in text_lower and len(name) > 3)
            score += min(entity_mentions * 3, 12.0)

            # Term frequency boost: words that appear frequently document-wide
            words = re.findall(r"\b[a-z]{4,}\b", text_lower)
            if words:
                avg_freq = sum(term_freq.get(w, 0) for w in words) / len(words)
                score += min(avg_freq * 2, 10.0)

            block.importance_score = min(round(score, 1), 100.0)

        return doc

    def _build_term_frequency(self, blocks: List[Block]) -> Dict[str, int]:
        all_text = " ".join(b.content.lower() for b in blocks)
        words = re.findall(r"\b[a-z]{3,}\b", all_text)
        freq = Counter(words)
        # Remove stop words
        stop_words = {
            "the", "and", "for", "are", "but", "not", "you", "all", "can",
            "her", "was", "one", "our", "out", "day", "get", "has", "him",
            "his", "how", "its", "may", "new", "now", "old", "see", "two",
            "who", "boy", "did", "its", "let", "put", "say", "she", "too",
            "use", "that", "this", "with", "have", "from", "they", "will",
            "been", "when", "your", "what", "said", "each", "which", "their",
            "time", "into", "than", "then", "some", "these", "would", "there",
            "more", "also", "after", "where", "about", "other", "were", "well"
        }
        return {w: c for w, c in freq.items() if w not in stop_words}
