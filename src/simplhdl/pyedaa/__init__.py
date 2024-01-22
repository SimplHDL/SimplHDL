import pyEDAA.ProjectModel as pm

from pathlib import Path
from typing import Optional
from .vhdllibrary import VHDLLibrary


class HDLLibrary(VHDLLibrary):
    pass


class HDLIncludeFile(pm.SourceFile):
    pass


class HDLSourceFile(pm.HDLSourceFile):
    _library: HDLLibrary

    def __init__(self,
                 path: Path = None, project: pm.Project = None,
                 design: pm.Design = None, fileset: pm.FileSet = None,
                 library: Optional[HDLLibrary] = None):
        super().__init__(path, project, design, fileset)
        self._library = library

    @property
    def Library(self) -> HDLLibrary:
        return self._library

    @Library.setter
    def Library(self, value) -> None:
        self._library = value


class VerilogIncludeFile(HDLIncludeFile, pm.HumanReadableContent):
    pass


class VerilogSourceFile(HDLSourceFile, pm.HumanReadableContent):
    pass


class SystemVerilogSourceFile(HDLSourceFile, pm.HumanReadableContent):
    pass


class VHDLSourceFile(HDLSourceFile, pm.HumanReadableContent):
    pass


class CocotbPythonFile(pm.CocotbPythonFile):
    pass


class TCLSourceFile(pm.TCLSourceFile):
    pass


class IPSpecificationFile(pm.File, pm.XMLContent):
    pass


class NetlistFile(pm.NetlistFile):
    pass


class EDIFNetlistFile(pm.EDIFNetlistFile):
    pass


class CSourceFile(pm.CSourceFile):
    pass


class File(pm.File):
    pass


class SourceFile(pm.SourceFile):
    pass


class SettingFile(pm.SettingFile):
    pass


class ConstraintFile(pm.ConstraintFile):
    pass


class QuartusIPSpecificationFile(IPSpecificationFile):
    pass


class VivadoIPSpecificationFile(IPSpecificationFile):
    pass


class SystemRDLSourceFile(File):
    pass


class ScalaBuildFile(File):
    pass


class ChiselBuildFile(ScalaBuildFile):
    pass

