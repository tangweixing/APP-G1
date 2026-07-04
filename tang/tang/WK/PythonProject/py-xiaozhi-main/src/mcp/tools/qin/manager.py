from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
# 改为导入 kiss_function（与 tools.py 中的函数名匹配）
from .tools import kiss_function


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


class QinManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])
        add_tool((
            "self.qin.trigger",  # 工具名称不变
            "触发亲一下动作（ID=7），拉起g1_arm_action_example.py脚本",
            tool_props,
            kiss_function  # 关联 kiss_function
        ))


_manager = None


def get_qin_manager():
    global _manager
    if _manager is None:
        _manager = QinManager()
    return _manager
