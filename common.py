from typing import Any, Callable
import asyncio

# Action takes program state and does something
ActionArgs = tuple[asyncio.subprocess.Process]

class IAction:
    def __call__(self, args: ActionArgs) -> None:
        pass

Action = IAction