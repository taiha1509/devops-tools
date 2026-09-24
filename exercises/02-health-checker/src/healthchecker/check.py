from concurrent.futures import ThreadPoolExecutor

import requests

from healthchecker.logger import get_logger

logger = get_logger(__name__)
def fetch_with_retries(url: str, retries: int):
    count = 0
    response = None
    while count < retries:
        try:
            response = requests.get(url)
            break
        except Exception as e:
            count += 1
            logger.warning('check.run', extra={'message': f'Retry calling to {url} {count} times'})
            continue
    return response

