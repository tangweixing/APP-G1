from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
# 改为导入 hug_function
from .tools import hug_function  # 关键修改：与tools.py中的函数名保持一致

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


class YongbaoManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])
        add_tool((
            "self.yongbao.trigger",  # 工具名称不变
            "触发拥抱动作，拉起g1_arm_action_example.py脚本",
            tool_props,
            hug_function  # 此处也需改为 hug_function
        ))


_manager = None


def get_yongbao_manager():
    global _manager
    if _manager is None:
        _manager = YongbaoManager()
    return _manager
