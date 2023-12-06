from argparse import ArgumentParser
from pathlib import Path
import asyncio
import yaml
from typing import Callable, Any, Union
import re
from actions import exit_program
from common import Action, ActionArgs, TimerInfo, Timers
from datetime import datetime, timedelta

# Takes one line of output and returns True if actions should be triggered
Trigger = Callable[[str], bool]
Triggers = dict[Trigger, list[Action]]

ACTION_FACTORY: dict[str, Callable[..., Action]] = {
    'exit_program': exit_program.Run}

STANDARD_OUT_TRIGGERS: Triggers = {}
STANDARD_ERROR_TRIGGERS: Triggers = {}
TIMERS: Timers = []


def load_action_factories() -> None:
    actions_dir = Path(__file__).parent/'actions'
    for entry in actions_dir.iterdir():
        if entry.suffix != '.py':
            continue

        if entry.stem.startswith('__'):
            continue

        ACTION_FACTORY[entry.stem] = getattr(__import__('actions', fromlist=[entry.stem]), entry.stem).Run


def _create_trigger(patern: re.Pattern) -> Trigger:
    def trigger(string: str):
        return patern.search(string) is not None
    return trigger


def _create_action(action_def: dict[str, Any]) -> Action:
    action = action_def['action']
    assert type(action) is str
    kwargs = action_def.get('kwargs', {})
    assert type(kwargs) is dict
    if action not in ACTION_FACTORY:
        raise RuntimeError(f'"{action}" is not known ACTION')
    return ACTION_FACTORY[action](**kwargs)


def _load_triggers(triggers: Triggers, cfg: dict[str, list[dict[str, Union[str, dict[str, Any]]]]]) -> None:
    for trigger_pattern, actions in cfg.items():
        trigger = _create_trigger(re.compile(trigger_pattern))
        triggers[trigger] = [_create_action(a_def) for a_def in actions]


def _load_timers(timers: Timers, cfg: dict[str, dict[str, Union[bool, dict[str, Any], list[Any]]]]) -> None:
    for name, info in cfg.items():
        if not 'duration' in info:
            raise RuntimeError(f'"duration" is not specified in timer: "{name}"')

        duration_cfg = info['duration']
        assert type(duration_cfg) is dict
        duration = timedelta(seconds=duration_cfg.get('seconds', 0), minutes=duration_cfg.get('minutes', 0), hours=duration_cfg.get('hours', 0))

        assert type(info['actions']) is list
        actions = [_create_action(a_def) for a_def in info['actions']]

        timerinfo = TimerInfo(name, duration, actions)
        if info.get('autostart', False):
            timerinfo.start = datetime.now()
        timers.append(timerinfo)


def load_config(path: Path) -> None:
    cfg = yaml.load(open(path, 'r', encoding='utf-8'), yaml.Loader)

    if 'stdout' in cfg:
        _load_triggers(STANDARD_OUT_TRIGGERS, cfg['stdout'])

    if 'stderr' in cfg:
        _load_triggers(STANDARD_ERROR_TRIGGERS, cfg['stderr'])

    if 'timers' in cfg:
        _load_timers(TIMERS, cfg['timers'])


async def control_output(reader: asyncio.StreamReader, triggers: Triggers, action_args: ActionArgs) -> None:
    while not reader.at_eof():
        line = (await reader.readline()).decode()
        print(line, flush=True, end='')
        for trigger, actions in triggers.items():
            if trigger(line):
                for action in actions:
                    action(action_args)


async def control_timers(proc: asyncio.subprocess.Process, timers: Timers, action_args: ActionArgs) -> None:
    while True:
        # program ended
        if proc.returncode is not None:
            break

        now = datetime.now()
        for timer in timers:
            if timer.start is None:
                continue
            if now - timer.start >= timer.duration:
                timer.start = None
                for action in timer.actions:
                    action(action_args)

        await asyncio.sleep(0.5)


async def execute_program(path: Path, *args: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        path,
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        stdin=asyncio.subprocess.PIPE
    )
    action_args = (proc, TIMERS)

    await asyncio.gather(
        control_output(proc.stdout, STANDARD_OUT_TRIGGERS,  # type: ignore
                       action_args),
        control_output(proc.stderr, STANDARD_ERROR_TRIGGERS,  # type: ignore
                       action_args),
        control_timers(proc, TIMERS, action_args)
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
