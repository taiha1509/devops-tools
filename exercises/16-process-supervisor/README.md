# E16 — `minivisor`: A Tiny Process Supervisor

**Linux track · after E09 · ~8-10 hours**

## The problem

A container runs a shell script that starts two workers in the background. On `docker stop`, it takes
exactly ten seconds to exit, every time, and the workers never flush their buffers. `ps` inside it
shows a growing list of `<defunct>` processes. A Kubernetes pod with the same image restarts in a loop
with exit code 137 and nobody is sure whether that's a crash or the kubelet.

Each of those is one fact about signals, exit codes, or PID 1. A supervisor is where they all meet.

## What you're building

```bash
minivisor run --config procs.yaml
```

```yaml
# procs.yaml
processes:
  - name: web
    cmd: ["python3", "-m", "http.server", "8080"]
    restart: always          # always | on-failure | never
  - name: worker
    cmd: ["python3", "worker.py"]
    restart: on-failure
    max_restarts: 5
stop_timeout_seconds: 8
```

It starts every process, restarts them per policy with backoff, forwards `SIGTERM`/`SIGINT` to all
children on shutdown, escalates to `SIGKILL` after `stop_timeout_seconds`, reaps everything, and
exits with a code that tells the caller what happened.

## Requirements

- **`subprocess.Popen`, not `os.system`.** Then, once it works, read how `Popen` is implemented
  (`fork` + `exec`, or `posix_spawn`) — write one paragraph in `DECISIONS.md`. You don't need to call
  `os.fork` yourself; you need to know what `Popen` does for you.
- **Exit codes are an API — decode them.** `Popen.returncode` is `N` for a normal exit and `-N` when
  killed by signal `N`. Shells and Kubernetes report the latter as `128 + N`: 137 is `SIGKILL` (9)
  — usually the OOM killer or a stop timeout — and 143 is `SIGTERM` (15). Put this mapping in a pure
  function with a table-driven test.
- **Restart policy is pure.** `should_restart(policy, exit_code, restarts_so_far) -> bool` and
  `backoff(restarts_so_far) -> seconds` (exponential, capped) live in `policy.py`. The loop that sleeps
  and calls them doesn't.
- **Reap your children.** A child that exits and isn't waited for becomes a zombie (`Z` in E13's
  `ptop`). Use `os.waitpid(-1, os.WNOHANG)` in a loop, or `Popen.poll()` on each — decide which and
  say why. Also reap *grandchildren* reparented to you if you're PID 1; `Popen.poll` can't see those.
- **Handle signals without doing work in the handler.** The handler sets a flag (or writes to a
  self-pipe); the main loop acts on it. Doing I/O in a Python signal handler is how you get
  re-entrancy bugs.
- **Graceful stop.** On `SIGTERM`: stop restarting, send `SIGTERM` to every child, wait up to
  `stop_timeout_seconds`, `SIGKILL` survivors, reap, exit `0` if every child exited cleanly and
  non-zero otherwise.
- **Structured logs** — one event per start, exit (with decoded code and signal name), restart, and
  shutdown. Same JSON formatter as E01.

## Acceptance criteria

- [ ] Same done bar as E01
- [ ] Unit tests for exit-code decoding and the restart policy, with no processes started
- [ ] Integration tests that start real short-lived children (`sys.executable -c ...`): one that
      exits 0, one that exits 3, one that kills itself with `SIGKILL`. These run fine on macOS.
- [ ] A test that sends `SIGTERM` to the supervisor and asserts a child that ignores `SIGTERM` is
      `SIGKILL`ed after the timeout
- [ ] The PID 1 experiment below, written up in `DECISIONS.md`

## The PID 1 experiment

Run your supervisor as PID 1 in a container:

```bash
docker run --rm --name mv -v "$PWD":/work -w /work -e UV_PROJECT_ENVIRONMENT=/tmp/venv \
  ghcr.io/astral-sh/uv:python3.12-bookworm-slim \
  uv run minivisor run --config procs.yaml
# other terminal:
time docker stop mv
```

Then run the same thing with `--init` (Docker injects `tini` as PID 1). Then remove your `SIGTERM`
handler and try both again. Record the four `docker stop` timings and explain them. The explanation
involves the fact that the kernel doesn't apply default signal actions to PID 1, and it is the
answer to the ten-second `docker stop` in the problem statement.

## Why this one matters

"What does exit code 137 mean?", "why is my container slow to stop?", and "what's a zombie process?"
come up in almost every DevOps and SRE interview loop. After this, each one is a thing you built and
measured rather than a fact you memorised.
