import logging

from typing import Dict, List
from enum import Enum, auto
from shlex import split


logger = logging.getLogger(__name__)


class Arg(Enum):

    flag = auto()
    unique = auto()
    add = auto()
    addvalue = auto()


class CLIExe:

    name: str
    args: List[str]
    window_exe: str
    linux_exe: str

    ARGS = {
        '-nc': Arg.flag,
        '-work': Arg.unique,
        '-f': Arg.add,
        '-F': Arg.add,
    }

    def add_arg(self, arg: str) -> None:
        self.args.append(arg)

    def args(self):
        return self.args


class ToolBase:

    name: str
    alias: List[str]
    executables: CLIExe

    def __init__(self):
        pass


def token_to_dict(token: str) -> Dict[str, str]:
    print(token)
    if token.startswith('+') or token.startswith('-'):
        if ' ' in token:
            name, value = token.split(' ', maxsplit=1)
        elif '=' in token:
            name, value = token.split('=', maxsplit=1)
        elif '+' in token:
            name, value = token[1:].split('+', maxsplit=1)
            name = f"+{name}"
        else:
            name, value = token, None
        return {name: value}


def tokenize(string: str) -> List[Dict[str, str]]:
    args = list()
    tokens = split(string)
    i = 0
    while i < len(tokens):
        if tokens[i].startswith('-'):
            if not tokens[i+1].startswith('-') and not tokens[i+1].startswith('+'):
                args.append(' '.join(tokens[i:i+2]))
                i += 1
            else:
                args.append(tokens[i])
        elif tokens[i].startswith('+'):
            args.append(tokens[i])
        i += 1
    return args


if __name__ == '__main__':
    args = "-work mywork --log runme.log -D name=value -full64 +incdir+includes"
    tokens = tokenize(args)
    for token in tokens:
        d = token_to_dict(token)
        print(d)
