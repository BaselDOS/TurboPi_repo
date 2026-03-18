import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from web_control.ai_modes.core.ai_engine import ask_ai
from web_control.ai_modes.executors.movement_executor import MovementExecutor
from web_control.ai_modes.executors.led_executor import LEDExecutor


class AICommandNode(Node):

    def __init__(self):

        super().__init__("ai_command_node")

        self.move_exec = MovementExecutor(self)
        self.led_exec = LEDExecutor(self)

        self.subscription = self.create_subscription(
            String,
            "ai_command",
            self.command_callback,
            10
        )

    def command_callback(self,msg):

        text = msg.data

        self.get_logger().info(f"User command: {text}")

        #result = ask_ai(text)
        result = {
            "commands":[
            {"type":"move","value":"forward"}
            ]
        }

        commands = result.get("commands",[])

        self.get_logger().info(str(commands))

        for cmd in commands:

            if cmd["type"] == "move":
                self.move_exec.execute(cmd)

            elif cmd["type"] == "led":
                self.led_exec.execute(cmd)


def main():

    rclpy.init()

    node = AICommandNode()

    rclpy.spin(node)

    node.destroy_node()

    rclpy.shutdown()


if __name__ == "__main__":
    main()
