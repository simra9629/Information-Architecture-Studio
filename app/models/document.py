from dataclasses import dataclass, field
from typing import List, Dict, Any
from enum import Enum


class BlockType(str, Enum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    QUOTE = "quote"
    CODE = "code"
    IMAGE = "image"
    CALLOUT = "callout"
    WARNING = "warning"
    TIMELINE_EVENT = "timeline_event"
    ENTITY = "entity"
    RELATIONSHIP = "relationship"
    DEFINITION = "definition"
    REFERENCE = "reference"
    TABLE = "table"
    DIVIDER = "divider"
    TASK = "task"


class ProjectType(str, Enum):
    STORY_BIBLE = "Story Bible"
    RESEARCH_NOTES = "Research Notes"
    PROJECT_PLAN = "Project Plan"
    WORLDBUILDING = "Worldbuilding Document"
    KNOWLEDGE_BASE = "Knowledge Base"
    DEBATE_PREP = "Debate Preparation"
    STUDY_NOTES = "Study Notes"
    COMPETITION_PLAN = "Competition Planning"
    UNKNOWN = "Document"


@dataclass
class Block:
    id: str
    type: BlockType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    importance_score: float = 0.0
    level: int = 0  # for headings

    def to_dict(self):
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "metadata": self.metadata,
            "importance_score": round(self.importance_score, 1),
            "level": self.level,
        }


@dataclass
class Section:
    id: str
    title: str
    level: int
    blocks: List[Block] = field(default_factory=list)
    subsections: List["Section"] = field(default_factory=list)

    def all_blocks(self) -> List[Block]:
        result = list(self.blocks)
        for sub in self.subsections:
            result.extend(sub.all_blocks())
        return result


@dataclass
class Document:
    id: str
    title: str
    description: str = ""
    theme: str = "academic"
    project_type: ProjectType = ProjectType.UNKNOWN
    type_confidence: float = 0.0
    sections: List[Section] = field(default_factory=list)
    all_blocks: List[Block] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_blocks_by_type(self, block_type: BlockType) -> List[Block]:
        return [b for b in self.all_blocks if b.type == block_type]

    def get_top_entities(self, n: int = 10) -> List[Block]:
        entities = self.get_blocks_by_type(BlockType.ENTITY)
        return sorted(entities, key=lambda b: b.importance_score, reverse=True)[:n]

    def get_critical_blocks(self, threshold: float = 70.0) -> List[Block]:
        return [b for b in self.all_blocks if b.importance_score >= threshold]
