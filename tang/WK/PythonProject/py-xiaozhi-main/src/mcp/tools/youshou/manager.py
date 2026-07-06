from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from .tools import youshou_function


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


class YoushouManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])
        add_tool((
            "self.youshou.trigger",
            "触发右手抬起动作（ID=12），拉起g1_arm_action_example.py脚本",
            tool_props,
            youshou_function
        ))


_manager = None


def get_youshou_manager():
    global _manager
    if _manager is None:
        _manager = YoushouManager()
    return _manager
