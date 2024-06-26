import os
import yaml

from typing import Optional, Dict, Type
from pathlib import Path
from argparse import Namespace
from fusesoc.config import Config
from fusesoc.capi2.core import Core
from fusesoc.capi2.coreparser import Core2Parser
from fusesoc.fusesoc import Fusesoc


from simplhdl.pyedaa.project import Project
from simplhdl.pyedaa.fileset import FileSet  # type: ignore
from simplhdl.pyedaa import (
    File, SystemVerilogSourceFile, VerilogSourceFile,
    VHDLSourceFile, ConstraintFile, VerilogIncludeFile,
    TCLSourceFile, QuartusQIPSpecificationFile, VivadoIPSpecificationFile,
    HDLLibrary, HDLSourceFile)

from simplhdl.parser import ParserFactory, ParserBase
from simplhdl.flow import FlowBase, FlowFactory


SIMPLHDL_FUSESOC_CONF = os.getenv('SIMPLHDL_FUSESOC_CONF')

FILETYPE_2014_MAP = {
    'systemVerilogSource': SystemVerilogSourceFile,
    'systemVerilogSourceInclude': VerilogIncludeFile,
    '.sv': SystemVerilogSourceFile,
    '.svh': VerilogIncludeFile,
    'verilogSource': VerilogSourceFile,
    'verilogSourceInclude': VerilogIncludeFile,
    '.v': VerilogSourceFile,
    '.vh': VerilogIncludeFile,
    'vhdlSource': VHDLSourceFile,
    '.vhd': VHDLSourceFile,
    '.vhdl': VHDLSourceFile,
    'tclSource': TCLSourceFile,
    '.tcl': TCLSourceFile,
    'SDC': ConstraintFile,
    '.sdc': ConstraintFile,
    'QIP': QuartusQIPSpecificationFile,
    '.qip': QuartusQIPSpecificationFile,
    'xci': VivadoIPSpecificationFile,
    '.xci': VivadoIPSpecificationFile,
    'xdc': ConstraintFile,
    '.xdc': ConstraintFile,
    'unknown': File,
}

@ParserFactory.register()
class FuseSocParser(ParserBase):

    _format_id: str = "CAPI=2:"

    def __init__(self):
        super().__init__()

    def is_valid_format(self, filename: Optional[Path]) -> bool:
        if filename is None:
            filenames = Path('.').glob('*.core')
        else:
            filenames = [filename]

        for filename in filenames:
            if filename.exists():
                with filename.open() as fp:
                    if fp.readline().strip() == self._format_id:
                        return True
            else:
                config = Config(SIMPLHDL_FUSESOC_CONF)
                fusesoc = Fusesoc(config)
                if fusesoc.get_core(str(filename)):
                    return True
        return False

    def parse(self, filename: Optional[Path], project: Project, args: Namespace, flow: FlowBase = None) -> FileSet:
        config = Config(SIMPLHDL_FUSESOC_CONF)
        config.no_export = True
        config.work_root = "_build"
        config.cache_root = "_build/cache"
        fusesoc = Fusesoc(config)

        if filename is None:
            filenames = Path('.').glob('*.core')
        else:
            filenames = [filename]

        for filename in filenames:
            if filename.exists():
                core = Core(Core2Parser(), filename)
            else:
                core = fusesoc.get_core(str(filename))
            break

        flow = FlowFactory.get_flow(args.flow, None, None, Path())
        print(type(flow))
        print(flow.category)

        edamfile, _ = fusesoc.get_backend(core, {"target": "sim", "tool": "icarus"})

        with open(edamfile, 'r') as fp:
            try:
                spec = yaml.safe_load(fp)
            except yaml.YAMLError as e:
                raise e


        cores = {}
        for f in spec.get('files', list()):
            name = f.get('core')
            if name in cores:
                cores[name].append(fileobj(f))
            else:
                cores[name] = [fileobj(f)]


        print(cores)


        raise SystemExit
#        last_lib = ''
#        i = 0
#        filesets = list()
#        for file in files:
#            if isinstance(file, HDLSourceFile):
#                if last_lib != file.Library.Name:
#                    library = HDLLibrary(file.Library.Name)
#                    fileset = FileSet(f"fs.{i}", vhdlLibrary=library)
#                    i += 1
#                    filesets.append(fileset)
#                last_lib = file.Library.Name
#            fileset.AddFile(file)
#
#        newfileset = FileSet('name')
#        for fileset in filesets:
#            newfileset.FileSet._fileSets[fileset.Name] = fileset
#
#        return newfileset



def fileobj(f: Dict) -> File:
    _class = get_file_type(f)
    file = _class(f.get('name'))
    if f.get('logical_name'):
        file.Library = HDLLibrary(f.get('logical_name'))
    return file


def get_file_type(f: Dict) -> Type[File]:
    type = f.get('file_type')
    if type is not None:
        fileclass = FILETYPE_2014_MAP.get(type, File)
        if f.get('is_include') and fileclass in [VerilogSourceFile, SystemVerilogSourceFile]:
            fileclass = VerilogIncludeFile
    else:
        fileclass = File
    return fileclass

