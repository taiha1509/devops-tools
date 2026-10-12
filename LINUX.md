# Linux Internals in Python — Exercises E13-E17

A side track to the main twelve. Each exercise rebuilds a small piece of a Linux tool you already use
(`ps`, `top`, `ss`, `df`, a process supervisor, `docker stats`) by reading the same kernel interfaces
the real tool reads. The point is not the tool. The point is that after building it, you know what
the real one is doing — which is exactly what an interviewer is probing when they ask "a container
keeps getting OOM-killed, walk me through it" or "disk is full but `du` says it isn't."

## Where this fits

These compete for the same 3-5 h/week as the main track, and the English track after that. Don't run
them as a parallel stream. Slot them in as breathers between main-track phases, one at a time:

| After | Do | Why then |
|---|---|---|
| E02 | [E13](exercises/13-proc-top/) | Same five-file shape as E01, no AWS, fast win |
| E04 | [E14](exercises/14-socket-table/) | Networking pairs well with health checks and inventory |
| E06 | [E15](exercises/15-disk-inode-checker/) | Closest cousin of E01's janitor — the other half of "disk full" |
| E09 | [E16](exercises/16-process-supervisor/) | Signals and exit codes are what CI runners and containers live on |
| E12 | [E17](exercises/17-cgroup-inspector/) | Capstone: the kernel under Docker and Kubernetes limits |

Skip any of them without guilt if the main track is behind. E16 and E17 have the highest interview
value per hour; if you only do two, do those.

## You are on a Mac. `/proc` is not.

macOS has no `/proc`, no `/sys/fs/cgroup`, and different `statvfs` and signal semantics in places.
Two consequences, both deliberate:

**1. Tests run on fixtures, on your Mac.** Every exercise takes a `--root` (or equivalent) pointing at
the directory that *plays the part of* `/proc` or `/sys/fs/cgroup`. In production that is `/proc`. In
tests it is `tmp_path`, populated with text you captured from a real Linux box. This is the same seam
as E01's `ArtifactStore` and the same idea as moto: the logic is tested against data you control; the
live system is a thin adapter.

**2. Live runs happen in a Linux container.** From an exercise directory:

```bash
docker run --rm -it \
  -v "$PWD":/work -w /work \
  -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
  ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
  bash
# inside:
uv sync && uv run <tool> --help
```

`UV_PROJECT_ENVIRONMENT` keeps the container's Linux venv out of your Mac's `.venv` — mixing the two
breaks both. Add `apt-get update && apt-get install -y procps iproute2 strace` inside when you want
the real tools to compare against. (E16 and E17 each say which extra `docker run` flags they need.)

**Capturing fixtures** is part of each exercise, not a chore before it. Run the container, `cat` the
files you need, and save them under `tests/fixtures/`. Capture a few awkward cases on purpose — each
brief tells you which.

## The shape (same as E01)

```
models.py    frozen dataclasses for the nouns
parse.py     pure functions: text in, models out. No I/O. This is where the tests live.
source.py    a Protocol + LiveSource(root=Path("/proc")). Tests pass root=tmp_path.
report.py    orchestration: read, parse, compute, return a result object
cli.py       typer, JSON logging to stdout, exit codes 0 / 1 / 2
```

(`parse.py` plays the part of E01's `policy.py`: the pure core.) Start each one by copying
`01-log-janitor/pyproject.toml` and renaming the package. Drop the boto3/moto dev dependencies —
nothing here touches AWS.

## The done bar

Identical to the main track, run on your Mac against fixtures:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy --strict src && uv run pytest
```

Plus each exercise's own acceptance criteria, which always include one **live comparison**: run your
tool and the real one side by side in the container and explain every difference you see. Put that
explanation in `DECISIONS.md`. "Mine says 41 processes, `ps` says 43 — the two extra were `ps` and the
shell that ran it" is exactly the sentence the exercise is for.

## Index

| # | Exercise | Rebuilds | Teaches |
|---|---|---|---|
| [E13](exercises/13-proc-top/) | `ptop` | `ps`, `top` | `/proc`, clock ticks, why CPU % needs two samples |
| [E14](exercises/14-socket-table/) | `sockstat` | `ss -tanp`, `netstat` | TCP states, byte order, socket → PID via inodes |
| [E15](exercises/15-disk-inode-checker/) | `diskcheck` | `df`, `df -i` | Inodes, reserved blocks, deleted-but-open files |
| [E16](exercises/16-process-supervisor/) | `minivisor` | supervisord, tini | fork/exec, signals, exit codes, zombies, PID 1 |
| [E17](exercises/17-cgroup-inspector/) | `cgpeek` | `docker stats`, `kubectl top` | cgroup v2, what a K8s limit actually is, OOM, throttling |

## Reading

Keep `man 5 proc` open for E13-E15 — on a Mac, read it at
[man7.org/linux/man-pages/man5/proc.5.html](https://man7.org/linux/man-pages/man5/proc.5.html). For
E17, the kernel's own
[cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html) is the reference;
blog posts about cgroups are frequently describing v1.
