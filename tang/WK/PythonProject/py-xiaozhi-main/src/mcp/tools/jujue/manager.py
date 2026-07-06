from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from .tools import jujue_function


class PropertyType(Enum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    STRING = "string"


@dataclass
class Property:
    name: str
    type: PropertyType
    description: str = ""
    default_value: any = None
    required: bool = False
    min_value: int = None
    max_value: int = None


@dataclass
class PropertyList:
    properties: List[Property] = field(default_factory=list)


class JujueManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])
        add_tool((
            "self.jujue.trigger",
            "触发拒绝动作（ID=13），拉起g1_arm_action_example.py脚本",
            tool_props,
            jujue_function
        ))


_manager = None


def get_jujue_manager():
    global _manager
    if _manager is None:
        _manager = JujueManager()
    return _manager
