from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from .tools import elevator_stairs_function


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


class ElevatorStairsManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])  # 无参数
        add_tool((
            "self.elevator_stairs.trigger",  # 工具名称
            "触发电梯/楼梯查询，响应“电梯”“楼梯”指令",
            tool_props,
            elevator_stairs_function  # 关联工具函数
        ))


_manager = None


def get_elevator_stairs_manager():
    global _manager
    if _manager is None:
        _manager = ElevatorStairsManager()
    return _manager