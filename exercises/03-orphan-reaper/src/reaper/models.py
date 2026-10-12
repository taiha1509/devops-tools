from moto.core.common_models import BaseModel

from pydantic import Field

class Policy(BaseModel):
    max_age_days: int = Field(gt=0)
    exclusive_tag: dict[str, str | int]
    dry_run: bool = False

    def parse(self):
        return self.max_age_days, self.exclusive_tag, self.dry_run