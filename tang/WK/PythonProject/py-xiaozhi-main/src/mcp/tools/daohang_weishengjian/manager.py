from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from .tools import toilet_function


# 手动定义模型类
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


class ToiletManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])  # 无参数
        add_tool((
            "self.toilet.trigger",  # 工具名称
            "响应厕所/卫生间查询，调用指定脚本",
            tool_props,
            toilet_function
        ))


_manager = None


def get_toilet_manager():
    global _manager
    if _manager is None:
        _manager = ToiletManager()
    return _manager
