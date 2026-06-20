"""Retry-with-backoff for transient tool/API failures.

Used to wrap external calls (e.g. the credit bureau) so a flaky service is retried
automatically before the case escalates — the TRANSIENT_FAILURE route in the policy.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class RetryExhausted(RuntimeError):
    """Raised when all retry attempts fail."""

    def __init__(self, attempts: int, last_error: Exception) -> None:
        super().__init__(f"Retries exhausted after {attempts} attempts: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


def call_with_retries(
    fn: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay: float = 0.0,
    transient_exceptions: tuple[type[Exception], ...] = (Exception,),
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call ``fn`` with up to ``max_retries`` retries on transient exceptions.

    Uses exponential backoff (``base_delay * 2**attempt``). ``base_delay=0`` makes it
    instant for tests. Raises :class:`RetryExhausted` if every attempt fails.
    """

    attempts = 0
    last_error: Exception | None = None
    while attempts <= max_retries:
        try:
            return fn()
        except transient_exceptions as exc:  # noqa: BLE001 — deliberate transient handling
            last_error = exc
            if attempts == max_retries:
                break
            if base_delay > 0:
                sleep(base_delay * (2**attempts))
            attempts += 1
    assert last_error is not None
    raise RetryExhausted(attempts + 1, last_error)
