import subprocess
import time

from flask import jsonify, request
from std_msgs.msg import Float32MultiArray

def register_control_routes(server):

    app = server.app
    robot = server.robot

    app.add_url_rule('/api/move', 'move', lambda: api_move(robot), methods=['POST'])
    app.add_url_rule('/api/rotate', 'rotate', lambda: api_rotate(robot), methods=['POST'])
    app.add_url_rule('/api/camera', 'camera', lambda: api_camera(robot), methods=['POST'])

    app.add_url_rule('/api/run_node', 'run_node', lambda: api_run_node(server), methods=['POST'])
    app.add_url_rule('/api/stop_node', 'stop_node', lambda: api_stop_node(server), methods=['POST'])


def api_move(robot):

    data = request.json or {}

    robot.move_x = float(data.get("x", 0))
    robot.move_y = float(data.get("y", 0))

    return jsonify({"status": "ok"})


def api_rotate(robot):
    data = request.json or {}
    direction = data.get("direction")

    if direction == "cw":
        robot.rotate_dir = 1
    elif direction == "ccw":
        robot.rotate_dir = -1
    else:
        robot.rotate_dir = 0

    return jsonify({"status": "ok"})


def api_camera(robot):
    data = request.json or {}

    robot.cam_pan = float(data.get("x", 0))
    robot.cam_tilt = float(data.get("y", 0))

    return jsonify({"status": "ok"})


def api_run_node(server):

    data = request.json or {}
    node = data.get("node")

    try:

        # stop previous process
        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            server.current_process = None
            time.sleep(0.5)

        # reset robot movement
        server.robot.move_x = 0.0
        server.robot.move_y = 0.0
        server.robot.rotate_dir = 0

        # JOYSTICK MODE
        if node == "joystick":

            server.robot.manual_control = True

            return jsonify({"message": "Joystick mode enabled"})


        # ALL OTHER MODES
        server.robot.manual_control = False


        if node == "body_control":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/body_control.py"]

        elif node == "pose":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/pose.py"]

        elif node == "avoidance":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/web_control/web_control/avoidance_node.py"]

        else:
            server.robot.manual_control = True
            return jsonify({"message": "Unknown node"}), 400


        # launch node
        server.current_process = subprocess.Popen(cmd)

        # wait for node to start
        time.sleep(2)

        # activate avoidance node services
        if node == "avoidance":

            subprocess.Popen([
                "ros2", "service", "call",
                "/avoidance/enter",
                "std_srvs/srv/Trigger"
            ])

            time.sleep(0.5)

            subprocess.Popen([
                "ros2", "service", "call",
                "/avoidance/set_running",
                "std_srvs/srv/SetBool",
                "{data: true}"
            ])


        return jsonify({"message": f"{node} started"})


    except Exception as e:

        server.robot.manual_control = True
        return jsonify({"message": str(e)}), 500

def api_stop_node(server):

    try:

        # stop running process
        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            server.current_process = None

        # stop avoidance node if it was running
        try:
            subprocess.run([
                "ros2", "service", "call",
                "/avoidance/set_running",
                "std_srvs/srv/SetBool",
                "{data: false}"
            ])
        except:
            pass

        # return control to joystick/manual mode
        server.robot.manual_control = True

        # reset movement
        server.robot.move_x = 0.0
        server.robot.move_y = 0.0
        server.robot.rotate_dir = 0

        # reset camera
        server.robot.cam_pan = 0.0
        server.robot.cam_tilt = 0.0

        return jsonify({"message": "Node stopped"})

    except Exception as e:

        return jsonify({"message": str(e)}), 500
