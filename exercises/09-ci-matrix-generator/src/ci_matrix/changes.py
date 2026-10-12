"""Working out what actually changed. The one impure module.

YOUR JOB: implement `merge_base` and `changed_files`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class GitError(Exception):
    """A git command failed. Degrade to build-everything, never to build-nothing."""


def merge_base(repo_root: Path, base_ref: str, head_ref: str = "HEAD") -> str:
    """The commit where `head_ref` diverged from `base_ref`.

    **Not `HEAD~1`.** This is the single most common bug in tools like this:

        * `HEAD~1` on a PR with more than one commit sees only the last commit's
          files, so a service changed in the first of five commits never builds.
        * After a merge commit, `HEAD~1` is one of the two parents and the diff
          is nonsense in a different way.

    `git merge-base <base> HEAD` is the answer, and on a GitHub PR the base to
    use is `github.event.pull_request.base.sha`.

    One practical trap: `actions/checkout` defaults to `fetch-depth: 1`, so the
    base commit **is not in the local clone** and `merge-base` fails. Either set
    `fetch-depth: 0` in the workflow or fetch the base ref explicitly. Note which
    you chose in `DECISIONS.md`; this costs everyone an afternoon once.

    Raises:
        GitError: the refs are not both present locally.
    """
    raise NotImplementedError


def changed_files(repo_root: Path, base_sha: str, head_ref: str = "HEAD") -> tuple[str, ...]:
    """Repo-relative paths changed between `base_sha` and `head_ref`.

    `git diff --name-only --no-renames <base>...<head>`. Two details:

        * **Three dots, not two.** `a..b` is "what is in b and not a" against the
          current tips; `a...b` diffs against the merge base, which is what a PR
          review actually shows.
        * `--no-renames` keeps a rename as a delete plus an add. A rename out of
          one service and into another must rebuild **both**, and rename
          detection hides that.

    Deleted files are included, and they matter: deleting a service's last source
    file is a change to that service. The "change touching a deleted service"
    acceptance case lives here.

    Returns:
        Sorted paths with forward slashes, so the output is deterministic.

    Raises:
        GitError: the diff failed.
    """
    raise NotImplementedError


__all__ = ["GitError", "changed_files", "merge_base"]
