from __future__ import annotations
from typing import Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

# Timers specifies that an amount of time has passed since important event
@dataclass
class TimerInfo:
    name: str
    duration: timedelta
    actions: list[Action]
    # None ~ timer is not running
    start: datetime | None = None

Timers = list[TimerInfo]

# Action takes (program state, timers) does something
ActionArgs = tuple[asyncio.subprocess.Process, list[TimerInfo]]

class IAction:
    def __call__(self, args: ActionArgs) -> None:
        pass

Action = IAction