"""
retry.py
--------
A simple retry decorator with exponential back-off, used to wrap
OpenEO batch job submission and other flaky network calls.
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from typing import Callable, Tuple, Type

logger = logging.getLogger(__name__)


def retry(
    max_attempts: int = 3,
    delay: float = 60.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[BaseException], ...] = (Exception,),
) -> Callable:
    """
    Decorator that retries the wrapped function on failure.

    Parameters
    ----------
    max_attempts : int
        Maximum number of total attempts (1 = no retry).
    delay : float
        Seconds to wait before the first retry.
    backoff : float
        Multiplier applied to *delay* after each failure.
    exceptions : tuple of exception types
        Only retry on these exception types.

    Example
    -------
    >>> @retry(max_attempts=3, delay=30)
    ... def flaky_call():
    ...     ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempt(s): %s",
                            func.__qualname__, attempt, exc,
                        )
                        raise
                    logger.warning(
                        "%s attempt %d/%d failed: %s — retrying in %.0fs …",
                        func.__qualname__, attempt, max_attempts, exc, current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator
