from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
# 导入当前模块的工具函数
from .tools import identify_function


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


class IdentifyManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])  # 无参数
        add_tool((
            "self.identify.trigger",  # 工具名称
            "必须调用此工具来识别用户身份。触发条件：用户询问[我是谁][认识我][认得我][知道我是谁吗][看看我是谁]等任何与身份识别相关的问题。此工具会使用相机拍照并执行人脸识别，必须调用才能回答用户的身份问题。不要直接回复[认不出你]，必须先调用此工具。",
            tool_props,
            identify_function  # 关联工具函数
        ))


_manager = None


def get_identify_manager():
    global _manager
    if _manager is None:
        _manager = IdentifyManager()
    return _manager
