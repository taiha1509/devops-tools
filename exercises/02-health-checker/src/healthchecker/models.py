from dataclasses import dataclass
from typing import Annotated, Literal
from pydantic import BaseModel, Field, HttpUrl

@dataclass(frozen=True)
class CheckConfig(BaseModel):
    timeout_seconds: int = Field(gt=0)
    retries: int = Field(gt=0)
    checks: list[Check] = Field(min_length=1)

@dataclass(frozen=True)
class Check(BaseModel):
    name: str = Field()
    url: HttpUrl
    expect_status: int = Field(gt=199, lt=600)
    expect_value: str | int | None
    expect_headers: dict[str, str] | None
    expect_json_path: str | None