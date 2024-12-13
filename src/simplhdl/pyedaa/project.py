import logging
import pyEDAA.ProjectModel as pm  # type: ignore

from typing import Dict, List, Optional
from pathlib import Path
from ..repo import Repo
from .design import Design
from . import (
    IPSpecificationFile, TCLSourceFile, CocotbPythonFile, SettingFile, HDLIncludeFile,
    ConstraintFile, VHDLSourceFile, VerilogSourceFile, SystemVerilogSourceFile)

logger = logging.getLogger(__name__)


class Project(pm.Project):

    _part: str
    _vhdlGenerics: Dict[str, str]
    _verilogParameters: Dict[str, str]
    _verilogDefines: Dict[str, str]
    _verilogPlusArgs: Dict[str, str]
    _hooks: Dict[str, List[str]]
    _repos: Dict[str, Repo]
    _reposdir: Optional[Path]
    _verilogSuppressions: List[str]

    def __init__(
        self,
        name: str,
        rootDirectory: Path = Path("."),
        vhdlVersion: pm.VHDLVersion = None,
        verilogVersion: pm.VerilogVersion = None,
        svVersion: pm.SystemVerilogVersion = None
    ):
        super().__init__(name, rootDirectory, vhdlVersion, verilogVersion, svVersion)
        self._vhdlGenerics = dict()
        self._verilogParameters = dict()
        self._verilogDefines = dict()
        self._verilogPlusArgs = dict()
        self._hooks = dict()
        self._repos = dict()
        self._reposdir = None
        self._part = None
        self._verilogSuppressions = []

    @property
    def ReposDir(self) -> Optional[Path]:
        return self._reposdir

    @ReposDir.setter
    def ReposDir(self, path: Path) -> None:
        self._reposdir = path

    def AddRepo(self, name: str, repo: Repo) -> None:
        self._repos[name] = Repo

    @property
    def Name(self) -> str:
        return super().Name

    @Name.setter
    def Name(self, value: str):
        self._name = value

    @property
    def Hooks(self) -> Dict[str, List[str]]:
        return self._hooks

    def AddHook(self, name, command) -> None:
        try:
            self._hooks[name].append(command)
        except KeyError:
            self._hooks[name] = [command]

    @property
    def PlusArgs(self) -> Dict[str, str]:
        return self._verilogPlusArgs

    def AddPlusArg(self, name: str, value: str) -> None:
        self._verilogPlusArgs[name] = value

    @property
    def Parameters(self) -> Dict[str, str]:
        return self._verilogParameters

    def AddParameter(self, name: str, value: str) -> None:
        self._verilogParameters[name] = value

    @property
    def Generics(self) -> Dict[str, str]:
        return self._vhdlGenerics

    def AddGeneric(self, name: str, value: str) -> None:
        self._vhdlGenerics[name] = value

    @property
    def Defines(self) -> Dict[str, str]:
        return self._verilogDefines

    def AddDefine(self, name: str, value: str) -> None:
        self._verilogDefines[name] = value

    @property
    def Suppressions(self) -> List[str]:
        return self._verilogSuppressions
    
    def AddSuppression(self, suppression: str) -> None:
        self._verilogSuppressions.append(suppression)

    @property
    def Part(self) -> str:
        return self._part

    @Part.setter
    def Part(self, value: str) -> None:
        self._part = value

    @pm.Project.DefaultDesign.setter
    def DefaultDesign(self, design: Design):
        self._defaultDesign = design

    def export_edam(self) -> Dict:
        """
        Convert the project object to the Edam format used
        by Edialize.
        """
        files = [file_to_edam(f) for f in self.DefaultDesign.Files()]
        name = self.DefaultDesign.Name
        hooks: Dict = dict()
        tool_options: Dict = dict()
        parameters: Dict = dict()
        toplevel = self.DefaultDesign.TopLevel

        return {
            'files': files,
            'name': name,
            'hooks': hooks,
            'tool_options': tool_options,
            'parameters': parameters,
            'toplevel': toplevel,
        }


def file_to_edam(file_obj: pm.File) -> Dict:
    """
    Convert File object to edam dictionary.
    """
    return {
        'name': str(file_obj.Path.absolute()),
        'file_type': filetype_to_edam(file_obj),
        'is_include_file': isinstance(file_obj, HDLIncludeFile),
        'logic_name': "work"  # file_obj.FileSet.VHDLLibrary
    }


def filetype_to_edam(file_obj: pm.File) -> str:  # noqa C901
    if file_obj.FileType == SystemVerilogSourceFile:
        return 'systemVerilogSource'
    elif file_obj.FileType == VerilogSourceFile:
        return 'verilogSource'
    elif file_obj.FileType == VHDLSourceFile:
        return 'vhdlSource-2008'
    elif file_obj.FileType == ConstraintFile and file_obj.Path.suffix == '.xdc':
        return 'xdc'
    elif file_obj.FileType == ConstraintFile and file_obj.Path.suffix == '.sdc':
        return 'SDC'
    elif file_obj.FileType == SettingFile and file_obj.Path.suffix == '.qsf':
        # TODO: edalize don't have a QSF file type
        logger.warning('qsf files are not support')
        return 'user'
    elif file_obj.FileType == TCLSourceFile:
        return 'tclSource'
    elif file_obj.FileType == IPSpecificationFile and file_obj.Path.suffix == '.ip':
        return 'IP'
    elif file_obj.FileType == IPSpecificationFile and file_obj.Path.suffix == '.qip':
        return 'QIP'
    elif file_obj.FileType == IPSpecificationFile and file_obj.Path.suffix == '.qsys':
        return 'QSYS'
    elif file_obj.FileType == CocotbPythonFile:
        return 'user'
    logger.warning(f"Unknown filetype: '{file_obj.FileType.__name__}' for file '{file_obj.Path}'")
    return 'user'
