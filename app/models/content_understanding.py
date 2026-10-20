from typing import Any, Optional

from pydantic import BaseModel


class ExtractedField(BaseModel):
    value: Any = None
    confidence: Optional[float] = None


class ContentUnderstandingResult(BaseModel):
    analyzer_id: str
    content: str
    fields: dict[str, ExtractedField]