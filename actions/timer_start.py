from common import ActionArgs, IAction
from datetime import datetime


class Run(IAction):
    def __init__(self, *, name: str) -> None:
        super().__init__()
        self.name = name

    def __call__(self, args: ActionArgs) -> None:
        timers = args[1]
        for timer in timers:
            if timer.name == self.name:
                # do not start already running timer
                if timer.start is None:
                    timer.start = datetime.now()
                break
        else:
            raise RuntimeError(f'timer "{self.name}" does not exist')
