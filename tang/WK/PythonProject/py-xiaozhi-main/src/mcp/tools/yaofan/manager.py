from typing import List, Dict, Set, Tuple
# src/mcp/tools/yaofan/manager.py
from dataclasses import dataclass, field
from enum import Enum
from .tools import yaofan_function


# 手动定义PropertyType枚举（如果models.py不存在）
class PropertyType(Enum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    STRING = "string"


# 手动定义Property类
@dataclass
class Property:
    name: str
    type: PropertyType
    description: str = ""
    default_value: any = None
    required: bool = False
    min_value: int = None
    max_value: int = None


# 手动定义PropertyList类
@dataclass
class PropertyList:
    properties: List[Property] = field(default_factory=list)


class YaofanManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])
        add_tool((
            "self.yaofan.trigger",
            "触发要饭动作（ID=10），拉起g1_arm_action_example.py脚本",
            tool_props,
            yaofan_function
        ))


_manager = None


def get_yaofan_manager():
    global _manager
    if _manager is None:
        _manager = YaofanManager()
    return _manager
