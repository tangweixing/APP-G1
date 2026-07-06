from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from .tools import bixin_function


# 定义属性类型枚举
class PropertyType(Enum):
    BOOLEAN = "boolean"
    INTEGER = "integer"
    STRING = "string"


# 定义属性类
@dataclass
class Property:
    name: str
    type: PropertyType
    description: str = ""
    default_value: any = None
    required: bool = False
    min_value: int = None
    max_value: int = None


# 定义属性列表类
@dataclass
class PropertyList:
    properties: List[Property] = field(default_factory=list)


# 比心工具管理器类
class BixinManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """注册比心工具到MCP服务器"""
        # 定义工具参数（比心功能无需参数）
        tool_props = PropertyList([])

        # 注册工具：名称、描述、参数、回调函数
        add_tool((
            "self.bixin.trigger",  # 工具名称（遵循self.module.action格式）
            "触发比心动作（ID=8），拉起g1_arm_action_example.py脚本",  # 工具描述
            tool_props,  # 无参数
            bixin_function  # 关联tools.py中的工具函数
        ))


# 全局管理器实例（单例模式）
_manager = None


def get_bixin_manager():
    global _manager
    if _manager is None:
        _manager = BixinManager()
    return _manager
