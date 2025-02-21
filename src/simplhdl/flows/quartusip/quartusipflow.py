try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files
import shutil
import logging
import re

from typing import Dict
from argparse import Namespace
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from simplhdl.flow import FlowFactory, FlowTools, FlowError
from simplhdl.flows.implementationflow import ImplementationFlow
from simplhdl.flows.encrypt.encryptflow import EncryptFlow
from simplhdl.resources.templates import quartusip as templates
from simplhdl.utils import generate_from_template
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa import (
    SystemVerilogSourceFile, VerilogSourceFile, VHDLSourceFile,
    VerilogIncludeFile, HDLSourceFile
)

logger = logging.getLogger(__name__)


@FlowFactory.register('quartus-ip')
class QuartusIpFlow(ImplementationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('quartus-ip', help='Quartus IP creation Flow')
        parser.add_argument(
            '--gui',
            action='store_true',
            help="Open project in Quartus GUI"
        )
        parser.add_argument(
            '--encrypt',
            action='store_true',
            help="Encrypt the HDL sources"
        )
        parser.add_argument(
            '--dse-args',
            default='',
            action='store',
            metavar='ARGS',
            help="Extra arguments for Quartus Design Space Explore command"
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.templates = templates
        self.tools.add(FlowTools.QUARTUS)

    def configure(self) -> None:
        self.is_tool_setup()
        self.toplevel = self.project.DefaultDesign.TopLevel
        if len(self.toplevel.split()) > 1:
            raise FlowError("The Quartus IP flow only allow one top level to be defined")
        if (self.project.Name == "default"):
            self.name = self.toplevel
        else:
            self.name = self.project.Name

        self.ipdir = self.builddir.joinpath('ip', self.name)
        rtldir = self.ipdir.joinpath('rtl')
        args = Namespace(
            no_encrypt=not self.args.encrypt,
            outdir=rtldir,
            vendors=None,
            inplace=None
        )
        self.encrypt = EncryptFlow(self.name, args, self.project, self.builddir)

    def generate(self) -> None:
        templatedir = resources_files(templates)
        environment = Environment(
            loader=FileSystemLoader(templatedir),
            trim_blocks=True)
        template = environment.get_template('_hw.tcl.j2')

        variables = {
            "name": self.name,
            "author": "author",
            "version": "0.0.0",
            "group": "group",
            "description": "NA",
            "files": dict(),
            "params": dict(),
            "ports": dict()
        }
        generate_from_template(
            template,
            self.ipdir.joinpath(f"{self.name}_hw.tcl"),
            variables,
            files=self.get_files(encrypt=self.args.encrypt)
        )

    def run(self) -> None:
        self.configure()
        self.generate()
        self.encrypt.run()

    def get_files(self, encrypt: bool = False):
        files = dict()
        for file in self.project.DefaultDesign.Files():
            if file.FileType in [SystemVerilogSourceFile, VerilogIncludeFile]:
                files[file.Path.name] = "SYSTEMVERILOG_ENCRYPT" if encrypt else "SYSTEMVERILOG"
            elif file.FileType == VerilogSourceFile:
                files[file.Path.name] = "VERILOG_ENCRYPT" if encrypt else "VERILOG"
            elif file.FileType == VHDLSourceFile:
                files[file.Path.name] = "VHDL_ENCRYPT" if encrypt else "VHDL"
            else:
                continue
        return files

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which('quartus_sh') is None:
            logger.error('quartus_sh: not found in PATH')
            exit = True
        if shutil.which('encrypt_1735') is None:
            logger.error('encrypt_1735: not found in PATH')
            exit = True
        if exit:
            raise FileNotFoundError("Quartus is not setup correctly")


def analyze_hdl(file: Path, filetype: HDLSourceFile) -> Dict:
    if filetype in [SystemVerilogSourceFile, VerilogSourceFile]:
        return analyze_verilog_module(file)
    elif filetype in [VHDLSourceFile]:
        return analyze_vhdl_entity(file)
    raise FlowError(f"{filetype.__name__}: Unsupported file type for VHDL or Verilog")


def analyze_verilog_module(file: Path):
    return {}


def analyze_vhdl_entity(file: Path):
    with file.open('r') as f:
        code = f.readlines()
    _ = read_entity(code)
    return {}


def read_entity(code: str) -> str:
    entity_start = re.compile(r'^\s*entity\s', re.IGNORECASE)
    entity_end = re.compile(r'^\s*end\s+entity', re.IGNORECASE)
    section_lines = []
    inside_entity = False

    for line in code:
        if not inside_entity and entity_start.match(line):
            inside_entity = True
        if inside_entity:
            section_lines.append(line)
            if entity_end.match(line):
                break
    return ''.join(section_lines)
