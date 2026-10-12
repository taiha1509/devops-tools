"""Parsing `/proc/self/mountinfo`. Pure.

**`mountinfo`, not `mounts`.** Two reasons, and the second is the one that bites:

  * it carries a mount ID, so you can tell two mounts of the same device apart
  * it **octal-escapes** whitespace in mount points. `/proc/mounts` does too, but
    mountinfo's field layout is unambiguous, whereas `mounts` has a space-separated
    device field that can itself contain escaped spaces

YOUR JOB: implement `unescape_octal`, `parse_mountinfo`, and `is_real_filesystem`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from diskcheck.models import Mount

PSEUDO_FILESYSTEMS = frozenset(
    {
        "proc",
        "sysfs",
        "devpts",
        "devtmpfs",
        "cgroup",
        "cgroup2",
        "securityfs",
        "pstore",
        "bpf",
        "debugfs",
        "tracefs",
        "configfs",
        "fusectl",
        "hugetlbfs",
        "mqueue",
        "autofs",
        "binfmt_misc",
        "efivarfs",
        "nsfs",
        "squashfs",
    }
)
"""Filesystems with no meaningful disk usage. An explicit **deny** list.

The brief asks you to defend this choice in `DECISIONS.md`, so here is the case:
a deny list fails *open* - a filesystem type nobody anticipated gets reported,
which is noisy but visible. An allow list fails *closed*: a new filesystem type
silently disappears from your disk report, and the one day that matters is the
day someone mounts something unusual and fills it.

Deliberately **not** here, because each is a judgement call:

    tmpfs    real usage, real exhaustion (it is RAM), and `/dev/shm` filling up
             is a genuine page - but there are a dozen tiny tmpfs mounts on a
             systemd box and reporting all of them is noise. Hence the
             `include_tmpfs` flag rather than a blanket decision.
    overlay  the container root. Real and important, but it appears **more than
             once** on a box running containers, and the lower layers are
             read-only so their "usage" is meaningless. Report the top one.
    zfs/btrfs  `statvfs` on these lies by design - free space depends on
             compression and snapshots, so the kernel's answer is an estimate.
             Worth a note in the output rather than exclusion.
"""


def unescape_octal(text: str) -> str:
    """Decode mountinfo's octal escapes.

    The kernel escapes four characters in paths: space (`\\040`), tab (`\\011`),
    newline (`\\012`) and backslash (`\\134`).

    `/mnt/my backup` appears as `/mnt/my\\040backup`. An implementation that does
    not decode this reports a mount point that does not exist, and one that
    splits the line on whitespace gets the field layout wrong entirely - which is
    why the fixture has a mount point with a space in it.

    Do **not** use `codecs.decode(text, "unicode_escape")`: it also mangles
    legitimate UTF-8 in paths, and a path is bytes, not latin-1. Replace the four
    sequences explicitly, and handle `\\134` **last** or you will decode the
    backslash of an escape you have not processed yet.
    """
    raise NotImplementedError


def parse_mountinfo(text: str) -> list[Mount]:
    """Parse the whole file.

    The format, per `proc(5)`::

        36 35 98:0 /mnt1 /mnt2 rw,noatime master:1 - ext3 /dev/root rw,errors=continue
        0  1  2    3     4     5          6          7 8    9        10

        0 mount ID        5 mount options
        1 parent ID       6 optional fields, **variable in number**
        2 major:minor     - a literal single hyphen: the separator
        3 root            8 filesystem type
        4 mount point     9 mount source (the device)
                         10 superblock options

    **Field 6 is variable-length.** Zero or more `tag:value` optional fields, then
    a literal `-`. So you cannot index from the left past field 5, and you cannot
    index from the right either because field 10 is optional in practice.

    The only correct approach: split on the standalone `-` separator. Everything
    before it is fields 0-6, everything after is type/source/superblock-options.
    Hardcoding an index here works on your laptop and breaks on a box with
    shared subtrees, which is to say on every Kubernetes node.

    Returns mounts in file order. Later mounts shadow earlier ones at the same
    point, and file order is what tells you which is on top.
    """
    raise NotImplementedError


def is_real_filesystem(mount: Mount, *, include_tmpfs: bool = False) -> bool:
    """Should this mount be reported?

    Excludes `PSEUDO_FILESYSTEMS`. `tmpfs` is behind a flag - see the note on
    that constant. `overlay` should be reported **once**: take the first (the
    container root) and skip the rest.
    """
    raise NotImplementedError


__all__ = ["PSEUDO_FILESYSTEMS", "is_real_filesystem", "parse_mountinfo", "unescape_octal"]
