import os
import logging
import shutil

from pathlib import Path
from typing import Any, List, Dict
from argparse import Namespace
from jinja2 import Template
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa.fileset import FileSet
from simplhdl.utils import sh, escape
from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.resources.templates import rivierapro as rivieraprotemplates
from simplhdl.flows.simulationflow import SimulationFlow

logger = logging.getLogger(__name__)


@FlowFactory.register('rivierapro')
class RivieraProFlow(SimulationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('rivierapro', help='Riviera PRO HDL Simulation Flow')
        parser.add_argument(
            '--step',
            action='store',
            choices=['compile', 'elaborate', 'simulate'],
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
            help="Open project in Riviera PRO GUI"
        )
        parser.add_argument(
            '--vsim-args',
            default='',
            action='store',
            metavar='args',
            help="Extra args for Riviera PRO vsim command"
        )
        parser.add_argument(
            '--vopt-args',
            default='',
            action='store',
            metavar='args',
            help="Extra args for Riviera PRO vopt command"
        )
        parser.add_argument(
            '--vmap-args',
            default='',
            action='store',
            metavar='args',
            help="Extra args for Riviera PRO vmap command"
        )
        parser.add_argument(
            '--vcom-args',
            default='',
            action='store',
            metavar='args',
            help="Extra args for Riviera PRO vcom command"
        )
        parser.add_argument(
            '--vlog-args',
            default='',
            action='store',
            metavar='args',
            help="Extra args for Riviera PRO vlog command"
        )
        parser.add_argument(
            '--seed',
            default=1,
            action='store',
            help="Seed to initialize random generator"
        )
        parser.add_argument(
            '--random-seed',
            default=1,
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
            help="Set the simulator timescale for Riviera PRO"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = rivieraprotemplates
        self.tools.add(FlowTools.RIVIERAPRO)

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
            environment.get_template('project.mk.j2')
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
        return f"-sv2k17 -work {library.Name}"

    def fileset_vhdl_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-2008 -work {library.Name}"

    def vlog_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-quiet')
        if self.args.timescale:
            args.add(f"-timescale {self.args.timescale}")
        for name in self.get_libraries().keys():
            args.add(f"-l {name}")
        if self.args.gui:
            args.add('-dbg')
        for name, value in self.project.Defines.items():
            args.add(f"+define+{name}={escape(value)}")
        if self.project.Suppressions.count is not None:
            args.add(f"-suppress {','.join(self.project.Suppressions)}")
        return ' '.join(list(args) + [self.args.vlog_args])

    def vcom_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-quiet')
        if self.args.gui:
            args.add('-dbg')
        return ' '.join(list(args) + [self.args.vcom_args])

    def vmap_args(self) -> str:
        args = set()
        return ' '.join(list(args) + [self.args.vmap_args])

    def vopt_args(self) -> str:
        return ""

    def vsim_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-quiet')
        for name in self.get_libraries().keys():
            args.add(f"-L {name}")
        for name, value in self.project.Generics.items():
            args.add(f"-g{name}={escape(value)}")
        for name, value in self.project.Parameters.items():
            args.add(f"-g{name}={escape(value)}")
        for name, value in self.project.PlusArgs.items():
            args.add(f"+{name}={escape(value)}")
        if self.args.gui:
            args.add('-dbg +access +r')
        if self.cocotb.enabled:
            args.add('+access +w_nets+p+*')
            # args.add('+access +w')
        args.add(f"-sv_seed {self.args.seed}")
        args.add(f"-random_seed {self.args.random_seed}")
        return ' '.join(list(args) + [self.args.vopt_args])

#    def vsim_args(self) -> str:
#        args = set()
#        args.add(f"-sv_seed {self.args.seed}")
#        if self.args.verbose == 0:
#            args.add('-quiet')
#        for name, value in self.project.PlusArgs.items():
#            args.add(f"+{name}={value}")
#        if self.args.gui:
#            args.add('-onfinish final')
#        else:
#            args.add('-onfinish exit')

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
        sh(['make', 'compile'], cwd=self.builddir, output=True)
        if step == 'compile':
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

    def is_tool_setup(self) -> None:
        if (shutil.which('vlog') is None or
                shutil.which('vsim') is None or
                shutil.which('vcom') is None or
                shutil.which('vlib') is None or
                shutil.which('vmap') is None):
            raise Exception("Riviera PRO is not setup correctly")
        # NOTE: If rivierapro's bin directory is appended to the PATH variable,
        #       the vdir command is found in /bin/vdir which is not the
        #       Riviera PRO vdir command
        vdir = Path(shutil.which('vdir'))
        vsim = Path(shutil.which('vsim'))
        if vdir.parent != vsim.parent:
            logger.warning(
                "Riviera PRO is not setup correctly. "
                f"The 'vdir' command is pointing to {vdir}, which "
                "is not part of the Riviera PRO installation. Try to "
                "prepend Riviera PRO to the PATH environment variable."
            )
            os.environ['PATH'] = f"{vsim.parent}:{os.environ['PATH']}"
