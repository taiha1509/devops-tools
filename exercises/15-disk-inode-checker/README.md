# E15 — `diskcheck`: Disk, Inodes, and the Space That Isn't There

**Linux track · after E06 · ~5-7 hours**

## The problem

Three pages from the same month:

1. `No space left on device`. `df -h` says the volume is 40% used.
2. `df` says the disk is 100% full. `du -sh /` adds up to half of that.
3. Disk alert fires at 95%. An engineer frees 5% and root processes keep writing, but the app user
   gets `ENOSPC` at what `df` reports as 95%.

All three have different causes, all three are normal Linux behaviour, and your janitor from E01 would
fix none of them. Build the tool that tells them apart.

## What you're building

```bash
diskcheck usage                          # per mount: bytes and inodes, like df -h and df -i
diskcheck usage --warn 80 --crit 90      # exit 1 if any mount crosses crit
diskcheck deleted-open                   # files deleted but still held open, with PID and size
diskcheck inode-hogs /var --top 10       # directories with the most entries
```

## Requirements

- **Read mounts from `/proc/self/mountinfo`**, not `/proc/mounts` — mountinfo has the mount ID and
  survives mount points with spaces (they're octal-escaped as `\040`; decode them). Skip pseudo
  filesystems (`proc`, `sysfs`, `cgroup2`, `tmpfs` unless asked, `overlay` only once) by an explicit
  allow/deny list you can defend in `DECISIONS.md`.
- **`os.statvfs` for numbers.** Know the three block counts: `f_blocks` total, `f_bfree` free
  including root's reserve, `f_bavail` free to ordinary users. ext4 reserves 5% for root by default.
  That's page #3. Report both, and compute "used %" the way `df` does:
  `used / (used + avail)`, not `used / total`.
- **Inodes are a separate budget.** `f_files` total, `f_ffree` free. A million 1-byte cache files
  exhaust inodes while bytes are barely touched. That's page #1.
- **Deleted-but-open files.** Walk `/proc/[pid]/fd/*`; a symlink target ending in ` (deleted)` is a
  file that `du` can't see and `df` still counts. Report PID, command, path, and size (`os.stat` on
  the fd link follows it to the still-open inode). That's page #2 — typically a log rotated without
  `copytruncate` or a restart.
- **Threshold logic is pure** and lives in `evaluate.py` (your `policy.py`): mount stats and
  thresholds in, list of findings out. Exit codes: 0 all clear, 1 a crit threshold was crossed,
  2 misuse.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] mountinfo fixture with a mount point containing a space, and one `overlay` root
- [ ] Tests for the `df` percentage formula with a nonzero reserve — the number must match `df`, not
      your intuition
- [ ] A test where bytes are 30% used and inodes are 99% used; `--crit 90` exits 1
- [ ] Live comparison against `df -h`, `df -i` and `lsof +L1` (if installed) in the container

## Capturing fixtures and reproducing the pages

`statvfs` results aren't files, so introduce a `StatSource` protocol and feed the pure code
`StatvfsResult`-shaped fixtures. To see the real behaviour in the container:

```bash
# page 1: inode exhaustion on a tiny filesystem
mkdir /tmp/tiny && mount -t tmpfs -o size=10M,nr_inodes=200 tmpfs /tmp/tiny
for i in $(seq 1 300); do touch /tmp/tiny/f$i; done
# page 2: deleted but open
python3 -c 'import os,time; f=open("/tmp/big","wb"); f.write(b"0"*50_000_000); f.flush(); os.remove("/tmp/big"); time.sleep(600)' &
```

`mount` needs `docker run --privileged` (or `--cap-add SYS_ADMIN`). Use it for this exercise only.

## Why this one matters

"Disk full but `du` disagrees" is one of the most common Linux interview questions for DevOps roles,
and it is also a real 3am page. Having built the tool, you'll answer with three causes and the way to
tell them apart, instead of one guess.
