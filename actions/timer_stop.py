from common import ActionArgs, IAction


class Run(IAction):
    def __init__(self, *, name: str) -> None:
        super().__init__()
        self.name = name

    def __call__(self, args: ActionArgs) -> None:
        timers = args[1]
        for timer in timers:
            if timer.name == self.name:
                timer.start = None
                break
        else:
            raise RuntimeError(f'timer "{self.name}" does not exist')
