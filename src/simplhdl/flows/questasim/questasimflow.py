try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files

import os
import re
import logging
import shutil

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from typing import Any, List, Dict, Optional
from argparse import Namespace
from jinja2 import Template
from simplhdl.pyedaa.project import Project
from simplhdl.utils import sh, escape
from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.resources.templates import questasim as questasimtemplates
from simplhdl.flows.simulationflow import SimulationFlow, FileSetWalker
from simplhdl.utils import generate_from_template

logger = logging.getLogger(__name__)

qrunfile = "project.qrun"


class Flag(list):

    def add(self, item):
        if item not in self:
            self.append(item)


@FlowFactory.register('questasim')
class QuestaSimFlow(SimulationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('questasim', help='QuestaSim HDL Simulation Flow')
        parser.add_argument(
            '--step',
            action='store',
            choices=['generate', 'compile', 'elaborate', 'simulate'],
            default='',
            help="flow step to run"
        )
        parser.add_argument(
            '-w',
            '--wavedump',
            nargs='?',
            const='wlf',
            choices=['wlf', 'vcd', 'evcd'],
            help="Dump waveforms using wlf, vcd or evcd format"
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help="Enable full debug capabilities"
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help="Clean project"
        )
        parser.add_argument(
            '--gui',
            nargs='?',
            const=os.getenv('SIMPLHDL_QUESTASIM_GUI', 'vsim'),
            choices=['vsim', 'visualizer'],
            help="Open project in QuestaSim GUI using vsim or visualizer"
        )
        parser.add_argument(
            '--qrun-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for QuestaSim qrun command"
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
        globals['qrunfile'] = qrunfile
        globals['wavedump'] = self.args.wavedump
        globals['filesets'] = self.get_filesets()
        globals['vlog_args'] = self.vlog_args()
        globals['vcom_args'] = self.vcom_args()
        globals['vopt_args'] = self.vopt_args()
        globals['vsim_args'] = self.vsim_args()
        globals['qrun_args'] = self.qrun_args()
        return globals

    def vlog_args(self) -> str:
        args = Flag()
        args.add('-sv')
        args.add('-suppress vlog-2720')
        for name, value in self.project.Defines.items():
            args.add(f"+define+{name}={escape(value)}")
        if self.project.Suppressions.count is not None:
            args.add(f"-suppress {','.join(self.project.Suppressions)}")
        return ' '.join(list(args) + [self.args.vlog_args])

    def vcom_args(self) -> str:
        args = Flag()
        args.add('-2008')
        return ' '.join(list(args) + [self.args.vcom_args])

    def vopt_args(self) -> str:
        args = Flag()
        if self.args.timescale:
            args.add(f"-timescale {self.args.timescale}")
        for name, value in self.project.Generics.items():
            args.add(f"-g{name}={escape(value)}")
        for name, value in self.project.Parameters.items():
            args.add(f"-g{name}={escape(value)}")
        if self.args.gui or self.args.debug:
            args.add('+acc')
            args.add('-debugdb')
            args.add('-fsmdebug')
        elif self.args.do or self.args.wavedump or self.cocotb.enabled:
            args.add('+acc=npr')
        return ' '.join(list(args) + [self.args.vopt_args])

    def vsim_args(self) -> str:
        args = Flag()
        args.add(f"-sv_seed {self.args.seed}")
        timescale = self.timescale()
        if timescale:
            args.add(timescale)
        if self.args.verbose == 0:
            args.add('-quiet')
        for name, value in self.project.PlusArgs.items():
            args.add(f"+{name}={escape(value)}")
        if self.cocotb.enabled:
            args.add(self.cocotb.args())
        if self.args.gui:
            args.add('-onfinish final')
        else:
            args.add('-onfinish exit')
        return ' '.join(list(args) + [self.args.vsim_args])

    def qrun_args(self) -> str:
        args = Flag()
        for top in self.cocotb.toplevels.split():
            if self.args.verbose > 0:
                args.add("-verbose")
            if self.version > 2023.0:
                args.add("-defaultHDLCompiler=vcom")
                args.add("-noautoorder")
            if self.is_uvm():
                args.add("-uvm")
            args.add(f"-top {top}")
        return list(args) + [self.args.qrun_args]

    def execute(self, step: str) -> None:
        """
        Execute the QuestaSim simulation flow.

        Parameters
        ----------
        step : str
            The step to execute. If not provided, the flow will execute
            the 'simulate' step.

        Returns
        -------
        None
        """
        if self.args.clean:
            sh(['qrun', '-clean'], cwd=self.builddir, output=True)
            return

        self.run_hooks('pre')

        if step == 'generate':
            return

        command = self.get_command(step)
        env = self.get_environment(command)

        sh(command, cwd=self.builddir, output=True, env=env)
        if step in ['simulate', '']:
            self.run_hooks('post')

    def get_command(self, step: str) -> List[str]:

        """
        Construct the command list to run qrun based on the given step and any command line arguments.

        Parameters
        ----------
        step : str
            The step to run. If None or not given, the default step is used.

        Returns
        -------
        command : List[str]
            The command list to execute qrun with.
        """
        command = ['qrun', '-f', qrunfile]

        if self.args.gui:
            if self.use_visualizer():
                command.append('-visualizer')
            command.append('-gui')
        elif self.args.step:
            if step == "elaborate":
                command.append('-optimize')
                return command
            command.append(f'-{step}')

        if self.args.do:
            if Path(self.args.do).exists():
                command += ['-do', str(Path(self.args.do).absolute())]
            else:
                command += ['-do', self.args.do]
        elif not self.use_visualizer() and not self.args.gui:
            command += ['-do', 'vsim-run.do']
        return command

    def get_environment(self, command: List[str]) -> Dict[str, str]:
        """
        Construct the environment for running qrun based on the given command and any
        enabled cocotb features.

        Parameters
        ----------
        command : List[str]
            The command to run qrun with.

        Returns
        -------
        env : Dict[str, str]
            A dictionary of environment variables to run qrun with.
        """
        if self.cocotb.enabled:
            env = self.cocotb.env()
        else:
            env = os.environ.copy()

        # Add the command  as environment variables for use in the
        # QuestaSim GUI and Tcl scripts
        env['SIMPLHDL_QUESTASIM_VSIM_COMMAND'] = ' '.join(command)
        return env

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
        if (shutil.which('qrun') is None):
            raise Exception("QuestaSim is not setup correctly")
        self.version = self.get_qrun_version()

    def has_visualizer(self) -> bool:
        if (shutil.which('visualizer') is None):
            return False
        else:
            return True

    def use_visualizer(self) -> bool:
        if self.args.gui == 'visualizer':
            if self.has_visualizer():
                return True
            else:
                logger.warning("Visualizer is not setup correctly")
        return False

    def generate(self):
        templatedir = resources_files(self.templates)
        env = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        templates: List[Template] = [
            env.get_template(f'{qrunfile}.j2'),
            env.get_template('vsim-run.do.j2'),
            env.get_template('modelsim.tcl.j2'),
            env.get_template('visualizer.tcl.j2')
        ]
        for template in templates:
            generate_from_template(template, self.builddir, self.get_globals())
        self.copy_memory_files()

    def get_qrun_version(self) -> float:
        output = sh(['qrun', '-version'], self.builddir)
        m = re.search(r'qrun\s+([\d.]+)', output)
        return float(m.group(1))

    def get_filesets(self):
        walker = FileSetWalker()
        filesets = list()
        for fileset in walker.walk(self.project.DefaultDesign.DefaultFileSet, reverse=True):
            filesets.append(fileset)
        return filesets
