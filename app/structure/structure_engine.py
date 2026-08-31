import re
from typing import List
from app.models.document import Block, BlockType, Document, ProjectType


PROJECT_SIGNALS = {
    ProjectType.STORY_BIBLE: [
        "character", "protagonist", "antagonist", "world", "magic", "kingdom",
        "chapter", "plot", "narrative", "lore", "faction", "race", "realm",
        "prophecy", "quest", "hero", "villain", "backstory"
    ],
    ProjectType.RESEARCH_NOTES: [
        "hypothesis", "methodology", "findings", "data", "analysis", "study",
        "experiment", "results", "citation", "source", "abstract", "conclusion",
        "bibliography", "literature", "research", "evidence"
    ],
    ProjectType.PROJECT_PLAN: [
        "milestone", "deadline", "sprint", "deliverable", "stakeholder", "scope",
        "timeline", "budget", "resource", "task", "objective", "kpi", "roadmap",
        "requirement", "risk", "dependency"
    ],
    ProjectType.WORLDBUILDING: [
        "geography", "culture", "religion", "economy", "government", "history",
        "language", "technology", "map", "region", "continent", "civilization",
        "species", "mythology", "cosmology"
    ],
    ProjectType.KNOWLEDGE_BASE: [
        "definition", "concept", "overview", "reference", "documentation",
        "guide", "tutorial", "faq", "glossary", "specification", "standard"
    ],
    ProjectType.STUDY_NOTES: [
        "formula", "theorem", "proof", "lecture", "exam", "quiz", "review",
        "chapter", "topic", "concept", "summary", "flashcard", "note"
    ],
    ProjectType.DEBATE_PREP: [
        "debate", "motion", "resolution", "rebuttal", "argument", "counterargument",
        "affirmative", "negative", "contention", "burden of proof", "cross-examination",
        "case", "framework", "impact", "clash", "evidence"
    ],
    ProjectType.COMPETITION_PLAN: [
        "competition", "contest", "tournament", "bracket", "entry", "submission",
        "judging", "criteria", "prize", "eligibility", "registration", "rules",
        "scoring", "round", "finalist", "qualifier"
    ],
}


class StructureEngine:
    """
    Refines block types using context and semantic patterns.
    Also detects overall project type.
    """

    INLINE_BOLD_CALLOUT = re.compile(
        r"\*\*(?:Important|Critical|Key Rule|Warning|Note|Danger|Alert)\*\*", re.IGNORECASE
    )
    YEAR_PATTERN = re.compile(r"\b(?:Year\s+\d{3,4}|\d{4})\b")

    def process(self, doc: Document) -> Document:
        self._refine_blocks(doc.all_blocks)
        doc.project_type, doc.type_confidence = self._detect_project_type(doc)
        return doc

    def _refine_blocks(self, blocks: List[Block]) -> None:
        for i, block in enumerate(blocks):
            if block.type == BlockType.PARAGRAPH:
                block.type = self._classify_paragraph(block.content, i, blocks)
            elif block.type == BlockType.HEADING:
                # Level-3 headings that look like proper names → entity
                if block.level >= 3 and self._looks_like_name(block.content):
                    block.type = BlockType.ENTITY

    def _classify_paragraph(self, text: str, idx: int, blocks: List[Block]) -> BlockType:
        t = text.strip()

        if self.INLINE_BOLD_CALLOUT.search(t):
            if re.search(r"\b(?:warning|danger|alert)\b", t, re.IGNORECASE):
                return BlockType.WARNING
            return BlockType.CALLOUT

        if re.match(r"^(?:Warning|Danger|Alert)\s*[:\-]", t, re.IGNORECASE):
            return BlockType.WARNING

        if re.match(r"^(?:Important|Critical|Key Rule|Note)\s*[:\-]", t, re.IGNORECASE):
            return BlockType.CALLOUT

        if re.match(r"^(?:Relationship|Allied with|Enemy of|Mentor to|Rival of|Friend of)", t, re.IGNORECASE):
            return BlockType.RELATIONSHIP

        if self.YEAR_PATTERN.match(t) or re.match(r"^\d{4}\s*[:\-]", t):
            return BlockType.TIMELINE_EVENT

        if re.match(r"^(?:Definition|Term|Glossary)\s*[:\-]", t, re.IGNORECASE):
            return BlockType.DEFINITION

        if re.match(r"^(?:See also|Reference|Source|Cf\.)\s*[:\-]", t, re.IGNORECASE):
            return BlockType.REFERENCE

        # After an entity block, short descriptive paragraphs are entity descriptions
        if idx > 0 and blocks[idx - 1].type == BlockType.ENTITY:
            if len(t) < 300:
                return BlockType.PARAGRAPH  # keep as paragraph but entity context handled by importance

        return BlockType.PARAGRAPH

    def _looks_like_name(self, text: str) -> bool:
        text = text.strip()
        if not text or text.endswith(":"):
            return False
        words = text.split()
        if not words or len(words) > 5:
            return False
        if any(any(ch.isdigit() for ch in w) for w in words):
            return False
        # Real names aren't typeset in full block capitals in running
        # text; that's a much stronger signal of a section label than a
        # proper name.
        if any(w.isupper() and len(w) > 1 for w in words):
            return False
        if all(w[0].isupper() for w in words if w[:1].isalpha()):
            # Exclude generic section titles
            generic = {"the", "a", "an", "and", "of", "in", "on", "at", "to", "for",
                       "overview", "summary", "introduction", "background", "notes",
                       "rules", "settings", "world", "timeline", "characters", "locations",
                       "chapter", "section", "part", "appendix",
                       "submitted", "by", "session", "class", "roll", "aim", "objective",
                       "objectives", "program", "declaration", "certificate",
                       "acknowledgement", "acknowledgment", "engagement", "school",
                       "college", "university", "department", "subject", "assignment",
                       "project", "report", "number", "date", "name"}
            if not any(w.lower().strip(":,&") in generic for w in words):
                return True
        return False

    def _detect_project_type(self, doc: Document) -> tuple:
        all_text = " ".join(b.content.lower() for b in doc.all_blocks)

        scores = {}
        for ptype, signals in PROJECT_SIGNALS.items():
            score = 0
            for s in signals:
                if " " in s or "-" in s:
                    # Multi-word and hyphenated signals like "burden of
                    # proof" or "cross-examination" don't survive a
                    # \b\w+\b split into single words, so they're matched
                    # as plain substrings instead.
                    score += all_text.count(s) * 3
                else:
                    # Single-word signals use a word-boundary match --
                    # plain substring counting let short signals like
                    # "quest" fire on unrelated words that merely contain
                    # them ("questioning", "conquest").
                    score += len(re.findall(r"\b" + re.escape(s) + r"\b", all_text))
            scores[ptype] = score

        # Bonus signals from block types
        entity_count = sum(1 for b in doc.all_blocks if b.type == BlockType.ENTITY)
        timeline_count = sum(1 for b in doc.all_blocks if b.type == BlockType.TIMELINE_EVENT)
        relationship_count = sum(1 for b in doc.all_blocks if b.type == BlockType.RELATIONSHIP)

        if entity_count > 3:
            scores[ProjectType.STORY_BIBLE] += entity_count * 3
            scores[ProjectType.WORLDBUILDING] += entity_count * 2
        if timeline_count > 2:
            scores[ProjectType.STORY_BIBLE] += timeline_count * 2
            scores[ProjectType.PROJECT_PLAN] += timeline_count * 2
        if relationship_count > 1:
            scores[ProjectType.STORY_BIBLE] += relationship_count * 3

        if not scores or max(scores.values()) == 0:
            return ProjectType.UNKNOWN, 0.0

        best_type = max(scores, key=scores.get)
        total = sum(scores.values())

        # A handful of incidental keyword hits scattered across an
        # otherwise unrelated document is weak evidence -- previously any
        # plurality winner, even one resting on a single word occurring
        # once or twice, was reported as up to 99% confident. Require a
        # minimum amount of total signal before committing to a specific
        # type at all, and report confidence as the winner's actual share
        # of the evidence rather than doubling it.
        if total < 6:
            return ProjectType.UNKNOWN, 0.0

        confidence = round((scores[best_type] / total) * 100, 1)
        return best_type, min(confidence, 95.0)
