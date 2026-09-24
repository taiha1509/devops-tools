# E02 — Config-Driven Health Checker

**Phase 1 · Scripts that survive being run unattended · ~5-6 hours**

## The problem

Your deploy pipeline's "smoke test" stage is a `curl` loop in a bash block. It checks three URLs,
it doesn't check status codes properly, and last month it passed a deploy where the API returned
`200 OK` with an HTML error page. Nobody can run it locally to debug it, and adding a fourth
endpoint means editing YAML inside a workflow file.

## What you're building

`healthcheck --config checks.yaml` — a post-deploy gate that reads its targets from config, runs
them concurrently, and fails the pipeline honestly.

```yaml
defaults:
  timeout_seconds: 5
  retries: 2
checks:
  - name: api-health
    url: https://api.example.com/healthz
    expect_status: 200
    expect_json_path: "$.status"
    expect_value: "ok"
  - name: static-assets
    url: https://cdn.example.com/app.js
    expect_status: 200
    expect_header: {content-type: "application/javascript"}
```

## Requirements

- **Concurrency.** Checks run in parallel, not in series. A twelve-endpoint suite shouldn't take
  twelve timeouts to fail. `concurrent.futures.ThreadPoolExecutor` is the right reach here — these
  are I/O-bound and you don't need an async rewrite to prove the point.
- **Per-check timeout, always set.** A request with no timeout hangs your pipeline forever.
- **Retries with backoff** — but only for transport errors and 5xx. Retrying a 404 is just being
  slow about failing.
- **Config validation up front.** A typo'd key fails with a clear message before any request goes
  out, not with a `KeyError` halfway through. Use `pydantic` — you'll need it again in E10.
- **Exit codes:** 0 all passed, 1 one or more checks failed, 2 config is invalid.
- **Output:** JSON lines as in E01, plus a human-readable summary table when stdout is a TTY. The
  pipeline reads the JSON; you read the table.

## Acceptance criteria

- [ ] Same done bar as E01 (ruff, mypy strict, pytest all clean)
- [ ] Tests cover: all-pass, one-fails, timeout, connection refused, retry-then-succeed, invalid
      config
- [ ] No real network calls in the test suite — stub the transport at a seam you control
- [ ] Twelve checks with a 5s timeout complete in well under 12s when several are slow
- [ ] `--check <name>` runs a single check for debugging

## Why this one matters

Two things, both of which recur for the rest of the roadmap. First, **a config-validating CLI is the
shape almost all internal tooling takes** — E10 is this pattern at ten times the size. Second, this
is your first exercise whose output another system consumes: the exit code *is* the product. Getting
"which failures are retryable" right is the same judgment you'll apply to throttling in E03.

## Stretch

Make it emit a JUnit XML report so CI systems render per-check results natively. It's an unglamorous
format and knowing it makes you useful in a specific way most people aren't.
