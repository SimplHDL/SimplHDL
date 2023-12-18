from argparse import Namespace
from pathlib import Path
from typing import Callable, Dict
from abc import ABCMeta, abstractmethod
from enum import Flag, auto

from .pyedaa.project import Project


class FlowBase(metaclass=ABCMeta):

    def __init__(self, name, args: Namespace, project: Project, builddir: Path):
        self.name = name
        self.args = args
        self.project = project
        self.builddir = builddir
        self.category: FlowCategory = FlowCategory.DEFAULT

    @classmethod
    @abstractmethod
    def parse_args(self, parser) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        pass


class SimulationFlow(FlowBase):
    pass


class ImplementationFlow(FlowBase):
    pass


class FlowCategory(Flag):
    DEFAULT = auto()
    SIMULATION = auto()
    IMPLEMENTATION = auto()


class FlowError(Exception):
    pass


class FlowFactory:
    """
    Factory for creating flows
    """

    registry: Dict[str, FlowBase] = dict()

    @classmethod
    def register(cls, name: str) -> Callable:

        def inner_wrapper(wrapped_class: FlowBase) -> 'FlowBase':
            if name in cls.registry:
                raise Exception(f"Flow {name} already exists.")
            cls.registry[name] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def get_flow(cls, name: str, args: Namespace, project: Project, builddir: Path) -> 'FlowBase':
        if name in cls.registry:
            return cls.registry[name](name, args, project, builddir)
        raise Exception(f"Couldn't find Flow named {name}")

    @classmethod
    def get_flows(cls) -> Dict[str, 'FlowBase']:
        return cls.registry
