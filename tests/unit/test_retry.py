"""T066: unit tests for tools/retry.py's recoverable vs. non-recoverable
failure categorization and exponential backoff behavior."""

from __future__ import annotations

import time

import pytest

from tools.retry import NonRecoverableError, RecoverableError, async_retry_call, retry_call


def test_succeeds_immediately_without_retrying():
    calls = {"n": 0}

    def func():
        calls["n"] += 1
        return "ok"

    assert retry_call(func, max_retries=3, base_delay_seconds=0.01) == "ok"
    assert calls["n"] == 1


def test_retries_recoverable_error_then_succeeds():
    calls = {"n": 0}

    def func():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RecoverableError("transient")
        return "ok"

    assert retry_call(func, max_retries=5, base_delay_seconds=0.01) == "ok"
    assert calls["n"] == 3


def test_gives_up_after_max_retries():
    calls = {"n": 0}

    def func():
        calls["n"] += 1
        raise RecoverableError("still failing")

    with pytest.raises(RecoverableError):
        retry_call(func, max_retries=2, base_delay_seconds=0.01)
    assert calls["n"] == 3  # initial attempt + 2 retries


def test_non_recoverable_error_is_never_retried():
    calls = {"n": 0}

    def func():
        calls["n"] += 1
        raise NonRecoverableError("bad credentials")

    with pytest.raises(NonRecoverableError):
        retry_call(func, max_retries=5, base_delay_seconds=0.01)
    assert calls["n"] == 1  # no retry attempted at all


def test_backoff_is_exponential():
    calls = {"n": 0}
    timestamps = []

    def func():
        timestamps.append(time.monotonic())
        calls["n"] += 1
        if calls["n"] < 4:
            raise RecoverableError("transient")
        return "ok"

    retry_call(func, max_retries=5, base_delay_seconds=0.02)

    gaps = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    # Each gap should be roughly double the previous one (0.02, 0.04, 0.08 ...)
    assert gaps[1] > gaps[0] * 1.5
    assert gaps[2] > gaps[1] * 1.5


@pytest.mark.asyncio
async def test_async_retry_call_retries_recoverable_error():
    calls = {"n": 0}

    async def func():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RecoverableError("transient")
        return "ok"

    result = await async_retry_call(func, max_retries=3, base_delay_seconds=0.01)
    assert result == "ok"
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_async_retry_call_propagates_non_recoverable_immediately():
    calls = {"n": 0}

    async def func():
        calls["n"] += 1
        raise NonRecoverableError("bad input")

    with pytest.raises(NonRecoverableError):
        await async_retry_call(func, max_retries=3, base_delay_seconds=0.01)
    assert calls["n"] == 1
