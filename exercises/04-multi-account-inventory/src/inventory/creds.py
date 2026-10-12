"""Cross-account credentials, and keeping them alive.

This is the single most useful boto3 pattern that is not in E01-E03, and it is on
the critical path for any estate-wide tooling you will ever write.

YOUR JOB: implement `assume_role_session` and `refreshable_session`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    import boto3

    from inventory.accounts import AccountConfig


class AssumeRoleDenied(Exception):
    """The trust policy said no. Not retryable, and not fatal to the run.

    One account with a broken trust policy must not end a fourteen-account sweep -
    it becomes a `CollectionFailure` with reason `assume_role_denied`.
    """


def assume_role_session(account: AccountConfig, *, session_name: str) -> boto3.Session:
    """Assume `account.role_arn` and return a Session bound to the result.

    The straightforward version: `sts:AssumeRole`, then build a `boto3.Session`
    from the returned `AccessKeyId` / `SecretAccessKey` / `SessionToken`.

    **Thread safety.** A botocore `Session` is not safe to share carelessly across
    threads. Create one per worker and know why: the client cache and the
    credential resolver underneath it are mutable shared state. Write the reason
    in `DECISIONS.md` - "I read it somewhere" is not the answer an interviewer is
    looking for.

    Raises:
        AssumeRoleDenied: on `AccessDenied` / `AccessDeniedException`. Translate
            the botocore error here so callers never have to pattern-match on
            error codes.
    """
    raise NotImplementedError


def refreshable_session(
    account: AccountConfig,
    *,
    session_name: str,
    now: Callable[[], float] | None = None,
) -> boto3.Session:
    """Like `assume_role_session`, but the credentials renew themselves.

    Assumed-role credentials are short-lived - one hour by default, and as little
    as fifteen minutes depending on the role. A sweep over fourteen accounts and
    four regions can outlive them, and the failure mode is nasty: the run is most
    of the way done when every remaining call starts returning
    `ExpiredTokenException`.

    `botocore.credentials.RefreshableCredentials.create_from_metadata` exists for
    exactly this. Knowing it exists is most of the battle; the shape is:

        * a refresh callback that re-calls `sts:AssumeRole` and returns a dict
          with `access_key`, `secret_key`, `token`, `expiry_time` (ISO-8601)
        * `RefreshableCredentials.create_from_metadata(metadata, refresh_using,
          method)` wired onto a `botocore.session.Session`'s credential resolver
        * `boto3.Session(botocore_session=...)` over the top

    `now` is injectable so a test can drive the clock past expiry without
    sleeping for an hour. Same reason `now` is a parameter in E01.

    Returns:
        A Session whose credentials survive a long sweep.
    """
    raise NotImplementedError


__all__ = ["AssumeRoleDenied", "assume_role_session", "refreshable_session"]
