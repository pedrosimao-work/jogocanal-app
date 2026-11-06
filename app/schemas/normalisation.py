from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

NameContext = Literal["club", "competition", "channel"]


class FallbackSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True, strict=True)
    canonical_name: str | None = Field(max_length=160, min_length=1)


@dataclass(frozen=True)
class NormalisedName:
    value: str
    method: str
    needs_review: bool
    cached: bool = False
