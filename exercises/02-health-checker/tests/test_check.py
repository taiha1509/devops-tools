import threading
from unittest.mock import patch, Mock, MagicMock

import requests
from pydantic import HttpUrl
from healthchecker.check import run_one_check, run_all_checks


def test_check_fails_on_wrong_status_code(init_check):
    with patch("healthchecker.check.requests.get") as mock_get:
        mock_get.return_value.status_code = 503
        check = init_check(name="backend", url="http://backend.app.svc.cluster.local", expect_status=200)
        result = run_one_check(check, 3, 5)

        assert not result.passed

def test_check_success_on_success_code(init_check):
    with patch("healthchecker.check.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        check = init_check(name="backend", url="http://backend.app.svc.cluster.local", expect_status=200)
        result = run_one_check(check, 3, 5)

        assert result.passed

def test_check_with_retries(init_check):
    with patch("healthchecker.check.requests.get") as mock_get:
        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            Mock(status_code=200)
        ]
        check = init_check(name="backend", url="http://backend.app.svc.cluster.local", expect_status=200)
        result = run_one_check(check, 3, 5)

        assert result.passed
        assert mock_get.call_count == 3

def test_too_few_retires_fail(init_check):
    with patch("healthchecker.check.requests.get") as mock_get:
        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            Mock(status_code=200)
        ]
        check = init_check(name="backend", url="http://backend.app.svc.cluster.local", expect_status=200)

        result = run_one_check(check, 2, 5)
        assert not result.passed
        assert mock_get.call_count == 2

def test_timeout_value_pass_to_requests(init_check):
    with patch("healthchecker.check.requests.get", autospec=True) as mock_get:
        mock_get.return_value = Mock(status_code=200)
        check = init_check(name="backend", url="http://backend.app.svc.cluster.local", expect_status=200)

        run_one_check(check, 1, 3)
        mock_get.assert_called_with(str(check.url), timeout=3)
        assert mock_get.call_args.kwargs["timeout"] == 3

def test_check_all_success(init_check):
    with patch("healthchecker.check.requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        check1 = init_check(name="backend", url="http://sit1.app.svc.cluster.local", expect_status=200)
        check2 = init_check(name="backend", url="http://sit2.app.svc.cluster.local", expect_status=200)
        check_results = run_all_checks([check1, check2], 3, 5)
        assert check_results[0].passed
        assert check_results[1].passed

        assert mock_get.call_count == 2
        assert mock_get.call_args[1]["timeout"] == 5

@patch("healthchecker.check.requests.get")
def test_check_all_fail_with_retries(mock_get, init_check):

    check1 = init_check(name="backend", url="http://sit1.app.svc.cluster.local", expect_status=200)
    check2 = init_check(name="backend", url="http://sit2.app.svc.cluster.local", expect_status=200)


    scripts = {
        u: iter([
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectTimeout(),
            Mock(status_code=200),
        ])
        for u in (str(check1.url), str(check2.url))
    }

    lock = threading.Lock()

    def fake_get(url: str, **kwargs):
        with lock:
            nxt = next(scripts[url])
        if isinstance(nxt, BaseException):
            raise nxt
        return nxt

    mock_get.side_effect = fake_get

    check_results = run_all_checks([check1, check2], 3, 5)

    assert all(r.passed for r in check_results)
    assert mock_get.call_count == 6

    assert all(c.kwargs["timeout"] == 5 for c in mock_get.call_args_list)