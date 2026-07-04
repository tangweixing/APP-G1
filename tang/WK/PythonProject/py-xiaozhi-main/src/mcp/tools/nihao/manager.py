from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
# 改为导入 hello_function（与 tools.py 中的函数名匹配）
from .tools import hello_function


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


class NihaoManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])
        add_tool((
            "self.nihao.trigger",  # 工具名称不变
            "触发你好动作（ID=6），拉起g1_arm_action_example.py脚本",
            tool_props,
            hello_function  # 关联 hello_function
        ))


_manager = None


def get_nihao_manager():
    global _manager
    if _manager is None:
        _manager = NihaoManager()
    return _manager
