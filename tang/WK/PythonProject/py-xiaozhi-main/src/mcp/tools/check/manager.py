from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
# 导入当前模块的工具函数（与tools.py中的函数名匹配）
from .tools import check_function


# 手动定义模型类（避免依赖models模块）
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


class CheckManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])  # 无参数
        add_tool((
            "self.check.trigger",  # 工具名称
            "触发查看操作，响应“看一下”“有什么”指令",
            tool_props,
            check_function  # 关联工具函数
        ))


_manager = None


def get_check_manager():
    global _manager
    if _manager is None:
        _manager = CheckManager()
    return _manager
