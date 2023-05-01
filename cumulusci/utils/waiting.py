import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


def retry(
    func: Callable,
    should_retry: Callable[[Exception], bool] = lambda e: True,
    retries: int = 5,
    retry_interval: int = 5,
    retry_interval_add: int = 30,
):
    while True:
        try:
            return func()
            break
        except Exception as e:
            if not (retries and should_retry(e)):
                raise
            if retry_interval:
                logger.warning(f"Sleeping for {retry_interval} seconds before retry...")
                time.sleep(retry_interval)
                if retry_interval_add:
                    retry_interval += retry_interval_add
            retries -= 1
            logger.warning(f"Retrying ({retries} attempts remaining)")


def poll(action: Callable):
    """poll for a result in a loop"""
    count = 0
    interval = 1
    while True:
        count += 1
        complete = action()
        if complete:
            break
        time.sleep(interval)
        if count % 3 == 0:
            interval += 1
