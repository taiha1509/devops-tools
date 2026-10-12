from dataclasses import dataclass
from typing import Annotated, Literal
from pydantic import BaseModel, Field, HttpUrl

class Check(BaseModel):
    name: str = Field()
    url: HttpUrl
    expect_status: int = Field(gt=199, lt=600)
    expect_value: str | int | None = None
    expect_headers: dict[str, str] | None = None
    expect_json_path: str | None = None

class CheckConfig(BaseModel):
    timeout_seconds: int = Field(gt=0)
    retries: int = Field(gt=0)
    checks: list[Check] = Field(min_length=1)

@dataclass
class CheckResult:
    name: str
    passed: bool = False
    error: str | None = None