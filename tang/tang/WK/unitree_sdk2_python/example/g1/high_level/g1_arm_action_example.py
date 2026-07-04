import time
import sys
from unitree_sdk2py.core.channel import ChannelSubscriber, ChannelFactoryInitialize
from unitree_sdk2py.g1.arm.g1_arm_action_client import G1ArmActionClient
from unitree_sdk2py.g1.arm.g1_arm_action_client import action_map
from dataclasses import dataclass


@dataclass
class TestOption:
    name: str
    id: int


option_list = [
    TestOption(name="release arm", id=0),
    TestOption(name="shake hand", id=1),  # 握手
    TestOption(name="high five", id=2),  # 手举高，你好
    TestOption(name="hug", id=3),  # 拥抱
    TestOption(name="high wave", id=4),  # 拜拜
    TestOption(name="clap", id=5),  # 拍手
    TestOption(name="face wave", id=6),  # 手举低，你好
    TestOption(name="left kiss", id=7),  # 飞吻
    TestOption(name="heart", id=8),  # 比心
    TestOption(name="right heart", id=9),  # 瞭望
    TestOption(name="hands up", id=10),  # 要饭
    TestOption(name="x-ray", id=11),  # 迪迦
    TestOption(name="right hand up", id=12),
    TestOption(name="reject", id=13),  # 拒绝1
    TestOption(name="right kiss", id=14),
    TestOption(name="two-hand kiss", id=15),

]


class UserInterface:
    def __init__(self):
        self.test_option_ = None

    def convert_to_int(self, input_str):
        try:
            return int(input_str)
        except ValueError:
            return None

    def terminal_handle(self):
        input_str = input("Enter id or name: \n")

        if input_str == "list":
            self.test_option_.name = None
            self.test_option_.id = None
            for option in option_list:
                print(f"{option.name}, id: {option.id}")
            return

        for option in option_list:
            if input_str == option.name or self.convert_to_int(input_str) == option.id:
                self.test_option_.name = option.name
                self.test_option_.id = option.id
                print(f"Test: {self.test_option_.name}, test_id: {self.test_option_.id}")
                return

        print("No matching test option found.")


def execute_action(arm_client, action_id):
    """执行指定ID的动作"""
    if action_id == 0:
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 1:
        arm_client.ExecuteAction(action_map.get("shake hand"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 2:
        arm_client.ExecuteAction(action_map.get("high five"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 3:
        arm_client.ExecuteAction(action_map.get("hug"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 4:
        arm_client.ExecuteAction(action_map.get("high wave"))
    elif action_id == 5:
        arm_client.ExecuteAction(action_map.get("clap"))
    elif action_id == 6:
        arm_client.ExecuteAction(action_map.get("face wave"))
    elif action_id == 7:
        arm_client.ExecuteAction(action_map.get("left kiss"))
    elif action_id == 8:
        arm_client.ExecuteAction(action_map.get("heart"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 9:
        arm_client.ExecuteAction(action_map.get("right heart"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 10:
        arm_client.ExecuteAction(action_map.get("hands up"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 11:
        arm_client.ExecuteAction(action_map.get("x-ray"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 12:
        arm_client.ExecuteAction(action_map.get("right hand up"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 13:
        arm_client.ExecuteAction(action_map.get("reject"))
        time.sleep(2)
        arm_client.ExecuteAction(action_map.get("release arm"))
    elif action_id == 14:
        arm_client.ExecuteAction(action_map.get("right kiss"))
    elif action_id == 15:
        arm_client.ExecuteAction(action_map.get("two-hand kiss"))
    else:
        print(f"Invalid action ID: {action_id}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} networkInterface [actionId]")
        print("  networkInterface: 网络接口")
        print("  actionId: 可选参数，直接执行的动作ID")
        sys.exit(-1)

    # 移除按键确认步骤，保留警告信息
    print("WARNING: Please ensure there are no obstacles around the robot while running this example.")

    # 初始化通道
    ChannelFactoryInitialize(0, sys.argv[1])

    # 创建机械臂客户端
    armAction_client = G1ArmActionClient()
    armAction_client.SetTimeout(10.0)
    armAction_client.Init()

    # 检查是否提供了动作ID参数
    if len(sys.argv) >= 3:
        try:
            action_id = int(sys.argv[2])
            # 验证动作ID是否有效
            if any(option.id == action_id for option in option_list):
                print(f"直接执行动作ID: {action_id}")
                execute_action(armAction_client, action_id)
                sys.exit(0)
            else:
                print(f"无效的动作ID: {action_id}")
                sys.exit(-1)
        except ValueError:
            print(f"无效的动作ID: {sys.argv[2]}，必须是整数")
            sys.exit(-1)

    # 如果没有提供动作ID，则进入交互模式
    test_option = TestOption(name=None, id=None)
    user_interface = UserInterface()
    user_interface.test_option_ = test_option

    print("Input \"list\" to list all test option ...")
    while True:
        user_interface.terminal_handle()

        print(f"Updated Test Option: Name = {test_option.name}, ID = {test_option.id}")

        if test_option.id is not None:
            execute_action(armAction_client, test_option.id)

        time.sleep(1)
