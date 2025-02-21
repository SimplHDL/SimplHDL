import logging

import simplhdl
import simplhdl.parsers
import simplhdl.flows
import simplhdl.generators

from typing import Iterator
from pkgutil import iter_modules, ModuleInfo
from importlib import import_module
from itertools import chain

logger = logging.getLogger(__name__)


def iter_namespace(package) -> Iterator[ModuleInfo]:
    modules = iter_modules(package.__path__, package.__name__ + '.')
    return modules


def load_builtin_plugins() -> None:
    """
    Loads builtin plugins.
    """
    import_module('simplhdl.info')
    import_module('simplhdl.run')
    import_module('simplhdl.flows.vcs.vcsflow')
    import_module('simplhdl.flows.questasim.questasimflow')
    import_module('simplhdl.flows.modelsim.modelsimflow')
    import_module('simplhdl.flows.xsim.xsimflow')
    import_module('simplhdl.flows.rivierapro.rivieraproflow')
    import_module('simplhdl.flows.quartusdse.quartusdseflow')
    import_module('simplhdl.flows.encrypt.encryptflow')
    import_module('simplhdl.flows.vsg.vsgflow')
    import_module('simplhdl.flows.verible.veribleflow')
    import_module('simplhdl.flows.lint.lintflow')
    import_module('simplhdl.flows.flake8.flake8flow')
    packages = chain(
        iter_namespace(simplhdl.parsers),
        iter_namespace(simplhdl.flows),
        iter_namespace(simplhdl.generators))
    plugins = {
        name: import_module(name) for _, name, _ in packages
    }
    logger.debug(plugins)


def load_external_plugins() -> None:
    """
    Loads external plugins.
    """
    try:
        from importlib.metadata import entry_points
    except ImportError:
        from importlib_metadata import entry_points

    try:
        plugins = entry_points(group='simplhdl.plugins')
    except TypeError:
        plugins = list(entry_points().get('simplhdl.plugins', list()))

    for plugin in plugins:
        plugin.load()


def load_plugins() -> None:
    """
    Loads all plugins, both builtin and external.
    """
    load_builtin_plugins()
    load_external_plugins()
