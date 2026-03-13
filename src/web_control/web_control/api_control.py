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

    if node == "body_control":
        cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/body_control.py"]

    elif node == "pose":
        cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/pose.py"]

    elif node == "joystick":
        cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/joystick.py"]

    else:
        return jsonify({"message": "Unknown node"}), 400

    try:
        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            time.sleep(0.5)

        server.current_process = subprocess.Popen(cmd)

        return jsonify({"message": f"{node} started"})

    except Exception as e:
        return jsonify({"message": str(e)}), 500


def api_stop_node(server):
    try:
        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            server.current_process = None
            return jsonify({"message": "Node stopped"})

        return jsonify({"message": "No node running"})

    except Exception as e:
        return jsonify({"message": str(e)}), 500
