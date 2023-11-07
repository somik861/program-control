from argparse import ArgumentParser
from pathlib import Path
import asyncio
import yaml
from typing import Callable, Any, Union
import re
from actions import exit_program
from common import Action, ActionArgs

# Takes one line of output and returns True if actions should be triggered
Trigger = Callable[[str], bool]
Triggers = dict[Trigger, list[Action]]

ACTION_FACTORY: dict[str, Callable[..., Action]] = {
    'exit_program': exit_program.Run}

STANDARD_OUT_TRIGGERS: Triggers = {}
STANDARD_ERROR_TRIGGERS: Triggers = {}

def load_action_factories() -> None:
    actions_dir = Path(__file__).parent/'actions'
    for entry in actions_dir.iterdir():
        if entry.suffix != '.py':
            continue

        if entry.stem.startswith('__'):
            continue

        ACTION_FACTORY[entry.stem] = getattr(__import__('actions', fromlist=[entry.stem]), entry.stem).Run

def load_config(path: Path) -> None:
    cfg = yaml.load(open(path, 'r', encoding='utf-8'), yaml.Loader)

    def create_trigger(patern: re.Pattern) -> Trigger:
        def trigger(string: str):
            return patern.search(string) is not None
        return trigger

    def load_actions(triggers: Triggers, cfg: dict[str, list[dict[str, Union[str, dict[str, Any]]]]]) -> None:
        for trigger_pattern, actions in cfg.items():
            trigger = create_trigger(re.compile(trigger_pattern))
            triggers[trigger] = []
            for action_def in actions:
                action = action_def['action']
                assert type(action) is str
                kwargs = action_def.get('kwargs', {})
                assert type(kwargs) is dict
                if action not in ACTION_FACTORY:
                    raise RuntimeError(f'"{action}" is not known ACTION')

                triggers[trigger].append(ACTION_FACTORY[action](**kwargs))

    if 'stdout' in cfg:
        load_actions(STANDARD_OUT_TRIGGERS, cfg['stdout'])

    if 'stderr' in cfg:
        load_actions(STANDARD_ERROR_TRIGGERS, cfg['stderr'])


async def control_output(reader: asyncio.StreamReader, triggers: Triggers, action_args: ActionArgs) -> None:
    while not reader.at_eof():
        line = (await reader.readline()).decode()
        print(line, flush=True, end='')
        for trigger, actions in triggers.items():
            if trigger(line):
                for action in actions:
                    action(action_args)


async def execute_program(path: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        path,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE
    )

    await asyncio.gather(
        control_output(proc.stdout, STANDARD_OUT_TRIGGERS, # type: ignore
                       (proc,)),  
        control_output(proc.stderr, STANDARD_ERROR_TRIGGERS, # type: ignore
                       (proc,)),  
    )


def execute(path: Path, *args: str) -> None:
    asyncio.run(execute_program(path, *args))


def main() -> None:
    # Lets hope no argument of program will start with newline :D
    parser = ArgumentParser(prefix_chars='\n')
    parser.add_argument('config', type=Path, help='Path to config (yaml)')
    parser.add_argument('exec', type=Path, help='Executable path')
    parser.add_argument('args', type=str, nargs='*',
                        help='Executable arguments')
    args = parser.parse_args()

    load_action_factories()
    load_config(args.config)
    execute(args.exec, *args.args)


if __name__ == '__main__':
    main()
