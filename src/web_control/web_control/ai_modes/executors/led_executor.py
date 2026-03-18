import random

from ros_robot_controller_msgs.msg import RGBStates, RGBState
from web_control.ai_modes.core.color_map import COLOR_MAP


class LEDExecutor:

    def __init__(self,node):

        self.node = node

        self.pub = node.create_publisher(
            RGBStates,
            "ros_robot_controller/set_rgb",
            10
        )

    def execute(self,cmd):

        v = cmd["value"]

        if v == "off":
            self.set_led(0,0,0)

        elif v == "random":

            self.set_led(
                random.randint(0,255),
                random.randint(0,255),
                random.randint(0,255)
            )

        elif v in COLOR_MAP:

            r,g,b = COLOR_MAP[v]

            self.set_led(r,g,b)

    def set_led(self,r,g,b):

        msg = RGBStates()

        led1 = RGBState()
        led1.index = 0
        led1.red = r
        led1.green = g
        led1.blue = b

        led2 = RGBState()
        led2.index = 1
        led2.red = r
        led2.green = g
        led2.blue = b

        msg.states = [led1,led2]

        self.pub.publish(msg)
