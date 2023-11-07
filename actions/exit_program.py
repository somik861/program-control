from common import ActionArgs, IAction
from time import sleep


class Run(IAction):
    def __init__(self, *, kind_kill_timeout: float = 5) -> None:
        super().__init__()

        self.kind_kill_timeout = kind_kill_timeout

    def __call__(self, args: ActionArgs) -> None:
        super().__call__(args)

        process = args[0]
        if self.kind_kill_timeout > 0:
            process.terminate()
            sleep(self.kind_kill_timeout)

        if process.returncode is None:
            process.kill()
