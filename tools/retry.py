"""Shared retry/backoff utility (plan.md §11 Error Recovery).

Failures are categorized as recoverable (API timeout, rate limiting, temporary
network failure — retried with exponential backoff) or non-recoverable
(invalid credentials, missing transcript, invalid configuration, corrupted
JSON — never retried, surfaced immediately).
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


class RecoverableError(Exception):
    """A transient failure worth retrying: timeouts, rate limits, network blips."""


class NonRecoverableError(Exception):
    """A failure that will not resolve itself: bad credentials, malformed input."""


def retry_call(
    func: Callable[[], T],
    *,
    max_retries: int = 3,
    base_delay_seconds: float = 0.5,
) -> T:
    """Synchronous retry with exponential backoff. Re-raises immediately on
    NonRecoverableError or any exception not derived from RecoverableError."""
    attempt = 0
    while True:
        try:
            return func()
        except RecoverableError:
            attempt += 1
            if attempt > max_retries:
                raise
            time.sleep(base_delay_seconds * (2 ** (attempt - 1)))


async def async_retry_call(
    func: Callable[[], Awaitable[T]],
    *,
    max_retries: int = 3,
    base_delay_seconds: float = 0.5,
) -> T:
    """Async counterpart of retry_call, for discord.py / async HTTP clients."""
    attempt = 0
    while True:
        try:
            return await func()
        except RecoverableError:
            attempt += 1
            if attempt > max_retries:
                raise
            await asyncio.sleep(base_delay_seconds * (2 ** (attempt - 1)))
