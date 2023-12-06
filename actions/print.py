from common import ActionArgs, IAction


class Run(IAction):
    def __init__(self, *, message: str = '', flush: bool = True, new_line: bool = True) -> None:
        super().__init__()
        self.message = message
        self.flush = flush
        self.end = '\n' if new_line else ''

    def __call__(self, args: ActionArgs) -> None:
        print(self.message, flush=self.flush, end=self.end)
