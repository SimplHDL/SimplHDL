import logging

from typing import Dict, List
from .tool import ToolBase, CLIExe

logger = logging.getLogger(__name__)


class Vcs(ToolBase):

    name: str
    alias: List[str]
    executables: Dict[str, CLIExe]

    def __init__(self):
        super().__init__()
        self.name = 'vcs'
        self.alias = [self.name, 'vcsmx']
        self.executables = {
            'vlogan': self.Vlogan(),
            'vhdlan': self.Vhdlan(),
            'vcs': self.Vcs(),
        }

    class Vlogan(CLIExe):

        def __init__(self) -> None:
            super().__init__()
            self.name = 'vlogan'
            self.args = list()
            self.window_exe = None
            self.linux_exe = 'vlogan'

    class Vhdlan(CLIExe):

        def __init__(self) -> None:
            super().__init__()
            self.name = 'vhdlan'
            self.args = list()
            self.window_exe = None
            self.linux_exe = 'vhdlan'

    class Vcs(CLIExe):

        def __init__(self) -> None:
            super().__init__()
            self.name = 'vcs'
            self.args = list()
            self.window_exe = None
            self.linux_exe = 'vcs'
