"""Worked examples of `unittest.mock.patch`, using this package as the subject.

The one rule that explains most patch failures: **patch the name where it is looked
up, not where it is defined.** `check.py` does `import requests` and then calls
`requests.get(...)`, so the lookup happens at call time on the `requests` module
object. That means both `patch("healthchecker.check.requests.get")` and
`patch("requests.get")` land on the same attribute here. If `check.py` had instead
done `from requests import get`, the module would hold its own reference and only
`patch("healthchecker.check.get")` would work.
"""

from __future__ import annotations

import threading
from unittest.mock import Mock, patch

import pytest
import requests

from healthchecker.check import run_all_checks, run_one_check
from healthchecker.models import CheckResult

URL = "http://backend.app.svc.cluster.local"


def _result(results: list[CheckResult], name: str) -> CheckResult:
    """`run_all_checks` appends in completion order, so never index by position."""
    found = [r for r in results if r.name == name]
    assert len(found) == 1, f"expected one result named {name!r}, got {results}"
    return found[0]


# --------------------------------------------------------------------------------
# 1. autospec=True — the mock inherits the real signature, so call assertions
#    normalise positional vs keyword. This is the reason to reach for autospec.
# --------------------------------------------------------------------------------

@patch("healthchecker.check.requests.get", autospec=True)
def test_autospec_normalises_positional_and_keyword(mock_get, init_check):
    mock_get.return_value = Mock(status_code=200)
    check = init_check(name="backend", url=URL, expect_status=200)

    run_one_check(check, 1, 5)

    # Production code calls get(url, timeout=5) positionally. Because the mock
    # carries requests.get's real signature, mock binds both spellings to the same
    # BoundArguments, so either assertion matches.
    mock_get.assert_called_once_with(str(check.url), timeout=5)
    mock_get.assert_called_once_with(url=str(check.url), timeout=5)


def test_without_autospec_the_keyword_spelling_fails(init_check):
    """Same assertion, no spec: mock compares raw args and the two differ."""
    with patch("healthchecker.check.requests.get") as mock_get:
        mock_get.return_value = Mock(status_code=200)
        check = init_check(name="backend", url=URL, expect_status=200)

        run_one_check(check, 1, 5)

        mock_get.assert_called_once_with(str(check.url), timeout=5)
        with pytest.raises(AssertionError):
            mock_get.assert_called_once_with(url=str(check.url), timeout=5)


# --------------------------------------------------------------------------------
# 2. patch.object — for when you already hold the object, no import string needed.
# --------------------------------------------------------------------------------

@patch.object(requests, "get", autospec=True)
def test_patch_object_on_an_imported_module(mock_get, init_check):
    mock_get.return_value = Mock(status_code=503)
    check = init_check(name="backend", url=URL, expect_status=200)

    assert not run_one_check(check, 1, 5).passed

    # Worth knowing: this patched requests.get process-wide for the duration of the
    # test, not just check.py's view of it. Narrower is safer when you have a choice.
    assert mock_get.call_count == 1


# --------------------------------------------------------------------------------
# 3. Patching a collaborator instead of the I/O boundary.
#
#    `fetch_with_retries` swallows every exception, so no `requests.get` mock can
#    ever make a future raise — which leaves the `except Exception` arm of
#    `run_all_checks` (check.py:37-39) unreachable. Patching `run_one_check`
#    itself is the only way to exercise it.
# --------------------------------------------------------------------------------

@pytest.mark.xfail(
    strict=True,
    raises=KeyError,
    reason=(
        "check.py:39 logs extra={'message': ...}, but 'message' is a reserved "
        "LogRecord attribute, so logging raises KeyError and it escapes "
        "run_all_checks. Fix is extra={'fields': {'error': str(e)}} - 'fields' "
        "because LoggerFormatter does a bare getattr(record, 'fields'). "
        "Remove this marker once fixed; strict=True will flag the XPASS."
    ),
)
@patch("healthchecker.check.run_one_check")
def test_worker_exception_becomes_a_failed_result(mock_run_one, init_check):
    def explode_for_bad(check, retries, timeout_seconds):
        if check.name == "bad":
            raise RuntimeError("worker died")
        return CheckResult(check.name, passed=True)

    mock_run_one.side_effect = explode_for_bad

    good = init_check(name="good", url="http://sit1.app.svc.cluster.local", expect_status=200)
    bad = init_check(name="bad", url="http://sit2.app.svc.cluster.local", expect_status=200)

    results = run_all_checks([good, bad], 3, 5)

    assert _result(results, "good").passed
    assert not _result(results, "bad").passed
    assert _result(results, "bad").error == "worker died"


# --------------------------------------------------------------------------------
# 4. Patching the module-level logger to assert on observable side effects.
#    `fetch_with_retries` emits one warning per failed attempt; nothing else checks it.
# --------------------------------------------------------------------------------

@patch("healthchecker.check.logger")
@patch("healthchecker.check.requests.get")
def test_each_retry_emits_one_warning(mock_get, mock_logger, init_check):
    # Decorators apply bottom-up, so the *bottom* patch is the *first* parameter.
    # Fixtures like init_check come after all injected mocks.
    mock_get.side_effect = requests.exceptions.ConnectionError()
    check = init_check(name="backend", url=URL, expect_status=200)

    assert not run_one_check(check, 3, 5).passed

    assert mock_get.call_count == 3
    assert mock_logger.warning.call_count == 3
    events = [c.args[0] for c in mock_logger.warning.call_args_list]
    assert events == ["check.run"] * 3
    last = mock_logger.warning.call_args_list[-1].kwargs["extra"]["fields"]["msg"]
    assert last == f"Retry calling to {check.url} 3 times"


# --------------------------------------------------------------------------------
# 5. new=... — supply your own double and mock injects nothing. Use this when you
#    want real behaviour (here: per-URL scripted responses) rather than a Mock.
# --------------------------------------------------------------------------------

class ScriptedGet:
    """A hand-rolled fake: thread-safe, keyed by URL, records its own calls."""

    def __init__(self) -> None:
        self.scripts: dict[str, list[object]] = {}
        self.calls: list[tuple[str, dict]] = []
        self._lock = threading.Lock()

    def script(self, url: str, *responses: object) -> None:
        self.scripts[url] = list(responses)

    def __call__(self, url: str, **kwargs):
        with self._lock:
            self.calls.append((url, kwargs))
            nxt = self.scripts[url].pop(0)
        if isinstance(nxt, BaseException) or (
            isinstance(nxt, type) and issubclass(nxt, BaseException)
        ):
            raise nxt
        return nxt


def test_new_lets_you_substitute_a_real_fake(init_check):
    check1 = init_check(name="sit1", url="http://sit1.app.svc.cluster.local", expect_status=200)
    check2 = init_check(name="sit2", url="http://sit2.app.svc.cluster.local", expect_status=200)

    # Key the script on str(check.url), never on the literal you typed: pydantic's
    # HttpUrl normalises and appends a trailing slash, and that normalised form is
    # what run_one_check hands to requests.get. Keying on the literal silently
    # misses, and fetch_with_retries swallows the resulting KeyError as "the
    # endpoint is down" - a mock that lies rather than fails.
    url1, url2 = str(check1.url), str(check2.url)

    fake = ScriptedGet()
    fake.script(url1, requests.exceptions.ConnectionError(), Mock(status_code=200))
    fake.script(url2, requests.exceptions.ConnectTimeout(), Mock(status_code=503))

    # `new=` is positional-friendly: patch(target, new). No mock argument appears in
    # the test signature, so there is nothing to assert on except your own fake.
    with patch("healthchecker.check.requests.get", fake):
        results = run_all_checks([check1, check2], 3, 5)

    assert _result(results, "sit1").passed
    assert not _result(results, "sit2").passed
    assert sorted(u for u, _ in fake.calls) == [url1, url1, url2, url2]
    assert all(kw["timeout"] == 5 for _, kw in fake.calls)
