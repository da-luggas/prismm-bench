from enum import Enum
from typing import Dict, List, Union
from pydantic import BaseModel, RootModel


class ReasoningLevel(str, Enum):
    OFF = "off"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class InconsistencyPartType(str, Enum):
    IMAGE = "image"
    TEXT = "text"


class InconsistencyPart(BaseModel):
    type: InconsistencyPartType
    page: int


class ImageBoundingBox(BaseModel):
    x: float
    y: float
    width: float
    height: float


class ImageInconsistencyPart(InconsistencyPart):
    type: InconsistencyPartType = InconsistencyPartType.IMAGE
    image_id: str
    bbox: ImageBoundingBox


class TextInconsistencyPart(InconsistencyPart):
    type: InconsistencyPartType = InconsistencyPartType.TEXT
    content: str
    line: int


class MCQItem(BaseModel):
    question: str
    correct: str
    incorrect: List[str]
    letters: List[str]


class MCQ(BaseModel):
    default: MCQItem
    binary_consistent: MCQItem
    binary_inconsistent: MCQItem
    edit: MCQItem
    default_natural: MCQItem
    part_pair: Union[MCQItem, dict] = {}


class AnnotationEntry(BaseModel):
    inconsistency_parts: List[Union[ImageInconsistencyPart, TextInconsistencyPart]]
    review_text: str
    category: str
    description: str
    mcq: MCQ


class AnnotationResults(RootModel):
    root: Dict[str, List[AnnotationEntry]]
