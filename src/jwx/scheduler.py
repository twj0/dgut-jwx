from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class ScheduleResult:
    attempts: int
    started_at: datetime
    finished_at: datetime
    last_error: str | None = None
    last_result: object | None = None


def sleep_until(target: datetime) -> None:
    while True:
        now = datetime.now(target.tzinfo)
        remaining = (target - now).total_seconds()
        if remaining <= 0:
            return
        time.sleep(min(0.5, remaining))


def run_polling(
    *,
    action: Callable[[], T],
    interval_s: float,
    max_attempts: int,
) -> ScheduleResult:
    started_at = datetime.now()
    attempts = 0
    last_error: str | None = None
    last_result: object | None = None

    while attempts < max_attempts:
        attempts += 1
        try:
            last_result = action()
            last_error = None
            return ScheduleResult(
                attempts=attempts,
                started_at=started_at,
                finished_at=datetime.now(),
                last_error=last_error,
                last_result=last_result,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(interval_s)

    return ScheduleResult(
        attempts=attempts,
        started_at=started_at,
        finished_at=datetime.now(),
        last_error=last_error,
        last_result=last_result,
    )

