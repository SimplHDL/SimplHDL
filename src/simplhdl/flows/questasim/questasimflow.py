import os
import logging
import shutil

from pathlib import Path
from typing import Any, List, Dict, Optional
from argparse import Namespace
from jinja2 import Template
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa.fileset import FileSet
from simplhdl.utils import sh, escape
from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.resources.templates import questasim as questasimtemplates
from simplhdl.flows.simulationflow import SimulationFlow

logger = logging.getLogger(__name__)


@FlowFactory.register('questasim')
class QuestaSimFlow(SimulationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('questasim', help='QuestaSim HDL Simulation Flow')
        parser.add_argument(
            '--step',
            action='store',
            choices=['generate', 'compile', 'elaborate', 'simulate'],
            default='simulate',
            help="flow step to run"
        )
        parser.add_argument(
            '-w',
            '--wave',
            action='store_true',
            help="Dump waveforms"
        )
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in QuestaSim GUI"
        )
        parser.add_argument(
            '--vsim-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for QuestaSim vsim command"
        )
        parser.add_argument(
            '--vopt-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for QuestaSim vopt command"
        )
        parser.add_argument(
            '--vmap-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for QuestaSim vmap command"
        )
        parser.add_argument(
            '--vcom-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for QuestaSim vcom command"
        )
        parser.add_argument(
            '--vlog-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for QuestaSim vlog command"
        )
        parser.add_argument(
            '--seed',
            type=int,
            default=1,
            action='store',
            help="Seed to initialize random generator"
        )
        parser.add_argument(
            '--random-seed',
            action='store_true',
            help="Generate a random seed to initialize random generator"
        )
        parser.add_argument(
            '--do',
            metavar='COMMAND',
            action='store',
            help="Do command to start simulation"
        )
        parser.add_argument(
            '--timescale',
            default='1ns/1ps',
            action='store',
            help="Set the simulator timescale for QuestaSim"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = questasimtemplates
        self.tools.add(FlowTools.QUESTASIM)

    def get_globals(self) -> Dict[str, Any]:
        globals = super().get_globals()
        globals['vlog_args'] = self.vlog_args()
        globals['vcom_args'] = self.vcom_args()
        globals['vopt_args'] = self.vopt_args()
        globals['vsim_args'] = self.vsim_args()
        return globals

    def get_project_templates(self, environment) -> List[Template]:
        return [
            environment.get_template('Makefile.j2'),
            environment.get_template('project.mk.j2'),
            environment.get_template('gui.do.j2')
        ]

    def get_cocotb_templates(self, environment):
        if self.cocotb.enabled:
            return [
                environment.get_template('cocotb.mk.j2')
            ]
        else:
            return list()

    def fileset_verilog_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-work {library.Name}"

    def fileset_systemverilog_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-sv -work {library.Name}"

    def fileset_vhdl_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-2008 -work {library.Name}"

    def vlog_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-quiet')
        for name in self.get_libraries().keys():
            args.add(f"-L {name}")
        for name, value in self.project.Defines.items():
            args.add(f"+define+{name}={escape(value)}")
        return ' '.join(list(args) + [self.args.vlog_args])

    def vcom_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-quiet')
        return ' '.join(list(args) + [self.args.vcom_args])

    def vmap_args(self) -> str:
        args = set()
        return ' '.join(list(args) + [self.args.vmap_args])

    def vopt_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-quiet')
        for name in self.get_libraries().keys():
            args.add(f"-L {name}")
        if self.args.timescale:
            args.add(f"-timescale {self.args.timescale}")
        for name, value in self.project.Generics.items():
            args.add(f"-g{name}={escape(value)}")
        for name, value in self.project.Parameters.items():
            args.add(f"-g{name}={escape(value)}")
        if self.args.gui or self.args.do or self.args.wave or self.cocotb.enabled:
            args.add('+acc=npr')
        return ' '.join(list(args) + [self.args.vopt_args])

    def vsim_args(self) -> str:
        args = set()
        args.add(f"-sv_seed {self.args.seed}")
        timescale = self.timescale()
        if timescale:
            args.add(timescale)
        if self.args.verbose == 0:
            args.add('-quiet')
        for name, value in self.project.PlusArgs.items():
            args.add(f"+{name}={escape(value)}")
        if self.args.gui:
            args.add('-onfinish final')
        else:
            args.add('-onfinish exit')

        return ' '.join(list(args) + [self.args.vsim_args])

    def get_library(self, fileset: FileSet) -> str:
        try:
            library = fileset.VHDLLibrary.Name
        except AttributeError:
            # TODO: This is a workaround The default fileset is FileSet
            #       which is bugged. Because it is empty we don't need it
            #       anyway and can just ignore it.
            library = ''
        return library

    def execute(self, step: str) -> None:
        self.run_hooks('pre')

        if step == 'generate':
            return

        if step == 'compile':
            sh(['make', 'compile'], cwd=self.builddir, output=True)
            return

        if self.args.do:
            if Path(self.args.do).exists():
                os.environ['DO_CMD'] = f"-do {Path(self.args.do).absolute()}"
            else:
                os.environ['DO_CMD'] = f"-do '{self.args.do}'"

        if self.args.gui:
            command = ['make', 'gui']
        else:
            command = ['make', step]
        sh(command, cwd=self.builddir, output=True)
        if step == 'simulate':
            self.run_hooks('post')

    def run_hooks(self, name):
        try:
            for command in self.project.Hooks[name]:
                logger.info(f"Running {name} hook: {command}")
                sh(command.split(), cwd=self.builddir, output=True)
        except KeyError:
            # NOTE: Continue if no hook is registret
            pass

    def timescale(self) -> Optional[str]:
        """
        Sets the timescale for VHDL based on the Verilog timescale
        resolution.
        """
        if self.args.timescale.endswith('ps'):
            return "-t ps"
        elif self.args.timescale.endswith('fs'):
            return "-t fs"

    def is_tool_setup(self) -> None:
        if (shutil.which('vlog') is None or
                shutil.which('vsim') is None or
                shutil.which('vcom') is None or
                shutil.which('vlib') is None or
                shutil.which('vmap') is None):
            raise Exception("QuestaSim is not setup correctly")
        # NOTE: If questasim's bin directory is appended to the PATH variable,
        #       the vdir command is found in /bin/vdir which is not the
        #       QuestaSim vdir command
        vdir = Path(shutil.which('vdir'))
        vsim = Path(shutil.which('vsim'))
        if vdir.parent != vsim.parent:
            logger.warning(
                "QuestaSim is not setup correctly. "
                f"The 'vdir' command is pointing to {vdir}, which "
                "is not part of the QuestaSim installation. Try to "
                "prepend Questa to the PATH environment variable."
            )
            os.environ['PATH'] = f"{vsim.parent}:{os.environ['PATH']}"
