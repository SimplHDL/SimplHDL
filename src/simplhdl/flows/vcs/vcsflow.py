from argparse import Namespace
import os
import logging
from pathlib import Path
import shutil
import re

from typing import Dict, Any, List
from jinja2 import Template
from simplhdl.pyedaa.fileset import FileSet
from simplhdl.pyedaa.project import Project
from simplhdl.utils import sh, escape
from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.resources.templates import vcs as vcstemplates
from ..simulationflow import SimulationFlow


logger = logging.getLogger(__name__)


@FlowFactory.register('vcs')
class VcsFlow(SimulationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('vcs', help='Vcs HDL Simulation Flow')
        parser.add_argument(
            '-s',
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
            help="Open project in DVE or Verdi GUI"
        )
        parser.add_argument(
            '--simv-args',
            default='',
            action='store',
            help="Extra args for Vcs simv command"
        )
        parser.add_argument(
            '--vcs-args',
            default='',
            action='store',
            help="Extra args for Vcs vcs command"
        )
        parser.add_argument(
            '--vhdlan-args',
            default='',
            action='store',
            help="Extra args for Vcs vhdlan command"
        )
        parser.add_argument(
            '--vlogan-args',
            default='',
            action='store',
            help="Extra args for Vcs vlogan command"
        )
        parser.add_argument(
            '--seed',
            default='1',
            action='store',
            help="Seed to initialize random generator"
        )
        parser.add_argument(
            '--random-seed',
            action='store_true',
            help="Generate a random seed to initialize random generator"
        )
        parser.add_argument(
            '--timescale',
            default='1ns/1ps',
            action='store',
            help="Set the simulator timescale for Verilog"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = vcstemplates
        self.tools.add(FlowTools.VCS)

    def get_globals(self) -> Dict[str, Any]:
        globals = super().get_globals()
        globals['vlogan_args'] = self.vlogan_args()
        globals['vhdlan_args'] = self.vhdlan_args()
        globals['vcs_args'] = self.vcs_args()
        globals['simv_args'] = self.simv_args()
        globals['parameters'] = {**self.project.Generics, **self.project.Parameters}
        globals['format'] = self.format
        return globals

    def format(self, value: str) -> str:
        """
        Format the parameter value in relation to it's type.
        """
        isformat_a = re.compile(r"^\d+#[0-9a-gA-G]+#")
        isformat_b = re.compile(r"^\d*'(h|d|b)[0-9a-fA-F]+")
        isformat_c = re.compile(r"^\d+\.\d+")

        if (
            value.isnumeric() or
            isformat_a.match(value) or
            isformat_b.match(value) or
            isformat_c.match(value)
        ):
            return value
        else:
            return f'"{value}"'

    def get_project_templates(self, environment) -> List[Template]:
        return [
            environment.get_template('Makefile.j2'),
            environment.get_template('synopsys_sim.setup.j2'),
            environment.get_template('project.mk.j2'),
            environment.get_template('vcs.parameters.j2'),
        ]

    def get_cocotb_templates(self, environment):
        if self.cocotb.enabled:
            return [
                environment.get_template('cocotb.mk.j2'),
                environment.get_template('pli.tab.j2')
            ]
        else:
            return list()

    def fileset_verilog_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"+v2k -work {library.Name}"

    def fileset_systemverilog_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-sverilog -work {library.Name}"

    def fileset_vhdl_args(self, fileset: FileSet) -> str:
        library = fileset.VHDLLibrary
        return f"-vhdl08 -work {library.Name}"

    def vlogan_args(self) -> str:
        args = set()
        for name, value in self.project.Defines.items():
            args.add(f"+define+{name}={escape(value)}")
        if self.args.verbose == 0:
            args.add('-q')
        elif self.args.verbose > 1:
            args.add('-V')
        if self.is_uvm():
            args.add('-ntb_opts uvm')
        if self.is_verdi():
            args.add('-kdb')
        if self.project.Suppressions.count is not None:
            args.add(f"-suppress={','.join(self.project.Suppressions)}")
        return ' '.join(list(args) + [self.args.vlogan_args]).strip()

    def vhdlan_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-q')
        elif self.args.verbose > 1:
            args.add('-verbose')
        if self.args.gui and self.is_verdi():
            args.add('-kdb')
        return ' '.join(list(args) + [self.args.vhdlan_args]).strip()

    def vcs_args(self) -> str:
        args = set()
        if self.args.verbose == 0:
            args.add('-q')
        if self.args.timescale:
            args.add(f"-timescale={self.args.timescale}")
        if self.is_uvm():
            args.add('-ntb_opts uvm')
        if self.args.gui:
            args.add('-debug_access+all')
            if self.is_verdi():
                args.add('-kdb')
        parameters = {**self.project.Generics, **self.project.Parameters}
        if parameters:
            args.add('-gfile vcs.parameters -lca')

        return ' '.join(list(args) + [self.args.vcs_args])

    def simv_args(self) -> str:
        args = set()
        if self.args.seed != '1':
            args.add(f"+ntb_random_seed={self.args.seed}")
        for name, value in self.project.PlusArgs.items():
            args.add(f"+{name}={escape(value)}")
        return ' '.join(list(args) + [self.args.simv_args])

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
        if (shutil.which('vlogan') is None or
                shutil.which('vhdlan') is None or
                shutil.which('vcs') is None):
            raise Exception("Vcs is not setup correctly")

    def is_verdi(self) -> bool:
        return (os.environ.get('SNPS_SIM_DEFAULT_GUI') == 'verdi' or
                os.environ.get('VERDI_HOME'))
