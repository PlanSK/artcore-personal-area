from typing import Callable, Any
from functools import wraps
import time


def time_of_run(function: Callable) -> Any:
    @wraps(function)
    def wrapper(*args, **kwargs):
        start = time.monotonic()
        func = function(*args, **kwargs)
        print(round(time.monotonic()-start, 3))
        return func
    return wrapper
