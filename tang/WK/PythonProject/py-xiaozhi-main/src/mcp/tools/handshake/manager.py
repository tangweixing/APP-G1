from typing import List, Dict, Tuple, Set, Union, Optional
from typing import List, Dict, Set, Tuple
# src/mcp/tools/handshake/manager.py
from dataclasses import dataclass, field
from enum import Enum
from .tools import handshake_function


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


class HandshakeManager:
    def __init__(self):
        pass

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        tool_props = PropertyList([])
        add_tool((
            "self.handshake.trigger",
            "触发握手动作，拉起mcp_handshake.py脚本",
            tool_props,
            handshake_function
        ))


_manager = None


def get_handshake_manager():
    global _manager
    if _manager is None:
        _manager = HandshakeManager()
    return _manager