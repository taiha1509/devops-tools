"""Account configuration: which accounts, which role, which regions.

YOUR JOB: implement `load_accounts`.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict


class AccountConfig(BaseModel):
    """One account to sweep. Given to you complete.

    `role_arn` is per-account because that is how it works in reality - the role
    name is usually uniform but the account number in the ARN is not.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    account_id: str
    role_arn: str
    regions: tuple[str, ...]
    label: str | None = None


def load_accounts(path: Path) -> tuple[AccountConfig, ...]:
    """Parse the accounts YAML into validated config objects.

    Expected shape::

        accounts:
          - account_id: "111111111111"
            role_arn: "arn:aws:iam::111111111111:role/InventoryReader"
            regions: ["eu-west-1", "us-east-1"]
            label: "prod"

    Let pydantic do the validating, and surface **all** validation errors at once
    rather than dying on the first - fourteen accounts means fourteen chances to
    have fat-fingered an ARN, and finding them one run at a time is miserable.
    (E10 makes this same point about its own config and it is not a coincidence.)

    Raises:
        ValueError: the file is unreadable, empty, or fails validation. The
            message must name the offending account, not just the field.
    """
    raise NotImplementedError


__all__ = ["AccountConfig", "load_accounts"]
