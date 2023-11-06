from common import ActionArgs, IAction
from time import sleep

class Run(IAction):
    def __call__(self, args: ActionArgs) -> None:
        super().__call__(args)

        process = args
        process.terminate()
        sleep(5)
        if process.returncode is None:
            process.kill()
        


       
