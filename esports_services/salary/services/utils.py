from typing import Callable, Any
from functools import wraps
import time
import logging


logger = logging.getLogger(__name__)


def execution_time_log(function: Callable) -> Any:
    @wraps(function)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        func = function(*args, **kwargs)
        logger.info(f'{function.__name__}: {round(time.monotonic()-start, 3)}s')
        return func
    return wrapper
