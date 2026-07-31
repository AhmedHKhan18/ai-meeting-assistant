"""Scheduler tool: APScheduler wrapper shared by the transcript poll and
retention cleanup (US2) and the morning/evening report triggers (US4).

Deliberately Foundational, not story-specific: US2 (P2) needs it before US4
(P4) does, so building it once here avoids a higher-priority story depending
on a lower-priority one (caught during /sp.analyze).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger


class SchedulerTool:
    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()

    def add_interval_job(
        self, func: Callable[[], Awaitable[None]], *, minutes: int, job_id: str
    ) -> None:
        self._scheduler.add_job(
            func, IntervalTrigger(minutes=minutes), id=job_id, replace_existing=True
        )

    def add_daily_job(
        self, func: Callable[[], Awaitable[None]], *, hour: int, minute: int, job_id: str
    ) -> None:
        self._scheduler.add_job(
            func, CronTrigger(hour=hour, minute=minute), id=job_id, replace_existing=True
        )

    def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.start()

    def shutdown(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)
