import shutil
import logging

from typing import List
from argparse import Namespace
from pathlib import Path

from simplhdl.flow import FlowFactory, FlowTools
from simplhdl.flows.implementationflow import ImplementationFlow
from simplhdl.utils import sh
from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa import SystemVerilogSourceFile, VerilogSourceFile, VHDLSourceFile, VerilogIncludeFile

logger = logging.getLogger(__name__)


@FlowFactory.register('encrypt')
class EncryptFlow(ImplementationFlow):

    @classmethod
    def parse_args(self, subparsers) -> None:
        parser = subparsers.add_parser('encrypt', help='Encrypt HDL source for diffent tool vendors')
        parser.add_argument(
            '--inplace',
            action='store_true',
            help="Place the encrypted file next to the source file"
        )
        parser.add_argument(
            '--no-encrypt',
            action='store_true',
            help="Disable encryption"
        )
        parser.add_argument(
            '--vendors',
            action='store',
            help="Vendor list to support"
        )
        parser.add_argument(
            '--outputdir',
            type=Path,
            dest='outdir',
            action='store',
            help='Output directory'
        )

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        super().__init__(name, args, project, builddir)
        self.tools.add(FlowTools.QUARTUS)

    def run(self) -> None:
        self.configure()
        self.execute()

    def configure(self) -> None:
        self.is_tool_setup()

    def execute(self):
        outputdir = self.args.outdir or self.builddir
        outputdir.mkdir(parents=True, exist_ok=True)

        for file in self.project.DefaultDesign.Files():
            if file.FileType in [SystemVerilogSourceFile, VerilogIncludeFile]:
                language = "systemverilog"
            elif file.FileType == VerilogSourceFile:
                language = "verilog"
            elif file.FileType == VHDLSourceFile:
                language = "vhdl"
            else:
                continue
            destFile = outputdir.joinpath(file.Path.name)

            if self.args.vendors:
                vendors = self.args.vendors.split(',')
            else:
                vendors = ["cadence", "mentor", "synopsys", "spyglass", "dsim", "veloce", "dcfcf"]

            if self.args.no_encrypt:
                shutil.copyfile(file.Path.absolute(), destFile.absolute())
            else:
                encrypt(file.Path, destFile.with_suffix(f"{destFile.suffix}p"), language, vendors)

    def is_tool_setup(self) -> None:
        exit: bool = False
        if shutil.which('encrypt_1735') is None:
            logger.error('encrypt_1735: not found in PATH')
            exit = True
        if exit:
            raise FileNotFoundError("Quartus is not setup correctly")


def encrypt(src: Path, dst: Path, language: str, vendors: List[str]) -> Path:
    """
    Encrypt a HDL source file using the 'encrypt_1735' tool.

    Parameters:
        src (Path): The source file path of the HDL file to be encrypted.
        dst (Path): The destination file path or directory for the encrypted file.
                    If dst is a directory, the source file name is appended.
        language (str): The language type of the HDL file (e.g., "systemverilog", "verilog", "vhdl").
        vendors (List[str]): A list of vendor names used to set up the simulation options.

    Returns:
        Path: The absolute path to the encrypted file.

    Example:
        encrypted_path = encrypt(Path("/path/to/source.v"), Path("/path/to/output"), "verilog", ["cadence", "mentor"])
    """
    destFile = dst.joinpath(src.name) if dst.is_dir() else dst
    command = [
        "encrypt_1735", str(src.absolute()),
        "--language", language,
        "--quartus",
        f"--simulation={','.join(vendors)}",
        "-of", f"{destFile.absolute()}"
    ]
    sh(command, output=True)
