from argparse import ArgumentParser
from pathlib import Path
import asyncio
import yaml
from typing import Callable, Any
import re
from actions import exit_program

# Action takes program state and does something
ActionArgs = asyncio.subprocess.Process
Action = Callable[[asyncio.subprocess.Process], None]

# Takes one line of output and returns True if actions should be triggered
Trigger = Callable[[str], bool]
Triggers = dict[Trigger, list[Action]]

KNOWN_ACTIONS: [str, Action] = {'exit_program': exit_program.Run}

STANDARD_OUT_TRIGGERS: Triggers = {}
STANDARD_ERROR_TRIGGERS: Triggers = {}


def load_config(path: Path) -> None:
    cfg = yaml.load(open(path, 'r', encoding='utf-8'))

    def create_trigger(patern: re.Pattern) -> Trigger:
        def trigger(string: str):
            return patern.search(string) is not None
        return trigger

    def load_actions(triggers: Triggers, cfg: dict[str, str]) -> None:
        for trigger_pattern, actions in cfg.items():
            trigger = create_trigger(trigger_pattern)
            triggers[trigger] = []
            for action in actions:
                if action not in KNOWN_ACTIONS:
                    raise RuntimeError(f'"{action}" is not known ACTION')

                triggers[trigger].append(KNOWN_ACTIONS[action])

    if 'stdout' in cfg:
        load_actions(STANDARD_OUT_TRIGGERS, cfg['stdout'])

    if 'stderr' in cfg:
        load_actions(STANDARD_ERROR_TRIGGERS, cfg['stderr'])


async def control_output(reader: asyncio.StreamReader, triggers: Triggers, action_args: ActionArgs) -> None:
    while not reader.at_eof():
        line = (await reader.readline()).decode()
        for trigger, actions in triggers:
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
        control_output(proc.stdout, STANDARD_OUT_TRIGGERS, proc),
        control_output(proc.stderr, STANDARD_ERROR_TRIGGERS, proc)
    )


def execute(path: Path, *args: str) -> None:
    asyncio.run(execute_program(path, *args))


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument('config', type=Path, help='Path to config (yaml)')
    parser.add_argument('exec', type=Path, help='Executable path')
    parser.add_argument('args', type=str, nargs='*', help='Executable arguments')
    args = parser.parse_args()

    load_config(args.config)
    execute(args.exec, *parser.args)


if __name__ == '__main__':
    main()
