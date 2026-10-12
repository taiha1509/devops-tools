from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from healthchecker.logger import get_logger
from healthchecker.models import Check, CheckResult

logger = get_logger(__name__)
def fetch_with_retries(url: str, retries: int, timeout_seconds: int):
    count = 0
    response = None
    while count < retries:
        try:
            response = requests.get(url, timeout=timeout_seconds)
            break
        except Exception as e:
            count += 1
            logger.warning('check.run', extra={'fields': {'msg': f'Retry calling to {url} {count} times'}})
            continue
    return response

def run_one_check(check: Check, retries: int, timeout_seconds: int) -> CheckResult:
    response = fetch_with_retries(str(check.url), retries, timeout_seconds)
    if response is None or getattr(response, 'status_code') != check.expect_status:
        return CheckResult(check.name, passed=False)
    return CheckResult(check.name, passed=True)

def run_all_checks(checks: list[Check], retries: int, timeout_seconds: int) -> list[CheckResult]:
    results: list[CheckResult] = []
    with ThreadPoolExecutor(max_workers=max(10, len(checks))) as pool:
        future_to_check = {pool.submit(run_one_check, check, retries, timeout_seconds): check for check in checks}
        for future in as_completed(future_to_check):
            check = future_to_check[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                results.append(CheckResult(check.name, passed=False, error=str(e)))
                logger.error('check.run', extra={'message': str(e)})


    return results
