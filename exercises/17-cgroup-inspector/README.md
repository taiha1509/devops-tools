# E17 — `cgpeek`: What a Container Limit Actually Is

**Linux track · after E12 · ~5-7 hours**

## The problem

A pod has `resources.limits.memory: 512Mi` and `limits.cpu: 500m`. It's restarted with `OOMKilled`
even though the app's dashboard says the heap is 300 MB. Its p99 latency is terrible, but CPU usage
never goes above 40% of the limit.

Kubernetes doesn't enforce either limit. The kernel does, through cgroups, and the kernel's view of
"memory" and "CPU" isn't the app's. This exercise reads that view directly.

## What you're building

```bash
cgpeek                    # the current process's cgroup: limits, usage, pressure
cgpeek --pid 1234         # another process's cgroup
cgpeek --watch 2          # re-sample every 2s and show deltas
```

Output, roughly:

```
cgroup   /system.slice/docker-3f2a…scope
memory   312.4 MiB / 512.0 MiB (61%)   anon 290.1  file 18.3   oom_kill 2
cpu      limit 0.50 cores (50000/100000)   throttled 38% of periods
pids     41 / 4096
```

## Requirements

- **cgroup v2 only.** Modern Docker, containerd and Kubernetes nodes all use v2. Detect v1 (no
  `cgroup.controllers` file at the root) and exit 2 with a clear message rather than guessing.
- **Find the cgroup.** `/proc/[pid]/cgroup` under v2 is a single line: `0::/some/path`. Join that path
  onto the cgroup mount (`/sys/fs/cgroup`). Inside a container with its own cgroup namespace, the path
  is often just `/` — handle it.
- **Memory.** `memory.max` is a byte count or the literal string `max` — model that as `int | None`,
  not a magic number. `memory.current` is usage. `memory.stat` splits it into `anon` (what the app's
  heap roughly is) and `file` (page cache, which counts toward the limit and is the usual answer to
  "the heap is only 300 MB"). `memory.events` has the `oom_kill` counter.
- **CPU.** `cpu.max` is `"<quota> <period>"` in microseconds, or `"max <period>"`. `50000 100000` is
  0.5 cores — which is exactly what `limits.cpu: 500m` becomes. `cpu.stat` has `nr_periods`,
  `nr_throttled`, and `throttled_usec`. Throttled ÷ periods is the number that explains the latency:
  a multi-threaded app can burn its whole 50 ms quota in the first 10 ms of each 100 ms period and
  then sit frozen for 90.
- **Pids.** `pids.max` and `pids.current`. Same `max` literal handling.
- **Deltas are pure.** `--watch` takes two samples; the throttle rate between them comes from a pure
  function over two `CpuStat` values, tested with fixtures. Same idea as E13's CPU %.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Fixtures for: unlimited (`max`) memory and CPU, a 512 MiB / 0.5 CPU container, and a v1 layout
      that must exit 2
- [ ] A test that `"max 100000"` parses to "no CPU limit", not to a number
- [ ] The OOM experiment below: `oom_kill` goes from 0 to 1 and your tool shows it
- [ ] The throttling experiment below: throttled % visibly rises, recorded in `DECISIONS.md`

## Experiments (in the container)

```bash
# --memory-swap equal to --memory disables swap, so the OOM killer can't be dodged
docker run --rm -it --memory=128m --memory-swap=128m --cpus=0.5 \
  -v "$PWD":/work -w /work -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
  ghcr.io/astral-sh/uv:python3.12-bookworm-slim bash
uv sync
# OOM: a child that allocates past the limit gets killed; the counter survives it
python3 -c 'x = bytearray(200 * 1024 * 1024)' ; echo "exit $?"   # expect 137
uv run cgpeek
# throttling: 4 busy threads against half a core
python3 -c 'import threading
def spin():
    while True: pass
[threading.Thread(target=spin, daemon=True).start() for _ in range(4)]
import time; time.sleep(30)' &
uv run cgpeek --watch 2
```

Compare against `docker stats` from your Mac. Note what `docker stats` shows for memory and whether it
includes page cache — the answer differs between Docker versions, which is exactly why reading the
kernel directly is worth knowing how to do.

## Why this one matters

`OOMKilled`, CPU throttling with low utilisation, and "why is my limit being hit when the app says
it's fine" are among the most common Kubernetes production issues. Having read `memory.stat` and
`cpu.stat` yourself, you can explain requests versus limits in terms of the files the kernel writes —
which is a Senior-level answer to a question most candidates answer at the YAML level.
