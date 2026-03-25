import subprocess
import time
from flask import request, jsonify


def register_control_routes(server):

    server.app.add_url_rule(
        '/api/run_node',
        'api_run_node',
        lambda: api_run_node(server),
        methods=['POST']
    )

    server.app.add_url_rule(
        '/api/stop_node',
        'api_stop_node',
        lambda: api_stop_node(server),
        methods=['POST']
    )

    server.app.add_url_rule(
        '/api/move',
        'api_move',
        lambda: api_move(server),
        methods=['POST']
    )

    server.app.add_url_rule(
        '/api/rotate',
        'api_rotate',
        lambda: api_rotate(server),
        methods=['POST']
    )

    server.app.add_url_rule(
        '/api/camera',
        'api_camera',
        lambda: api_camera(server),
        methods=['POST']
    )


# -------------------------------------------------
# RUN NODE
# -------------------------------------------------
def api_run_node(server):

    data = request.json or {}
    node = data.get("node")

    try:

        # kill previous node
        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            server.current_process = None
            time.sleep(0.5)

        # 🔥 RESET EVERYTHING
        server.robot.move_x = 0.0
        server.robot.move_y = 0.0
        server.robot.rotate_dir = 0
        server.robot.cam_pan = 0.0
        server.robot.cam_tilt = 0.0

        # -------------------------------------------------
        # JOYSTICK MODE
        # -------------------------------------------------
        if node == "joystick":

            server.robot.manual_control = True
            server.robot.stop_motion_once()

            return jsonify({"message": "Joystick mode enabled"})

        # -------------------------------------------------
        # ALL OTHER MODES → DISABLE UI CONTROL
        # -------------------------------------------------
        server.robot.manual_control = False
        server.robot.stop_motion_once()

        # -------------------------------------------------
        # SELECT NODE
        # -------------------------------------------------
        if node == "body_control":

            cmd = [
                "python3",
                "/home/ubuntu/ros2_ws/src/example/example/body_control.py"
            ]

        elif node == "pose":

            cmd = [
                "python3",
                "/home/ubuntu/ros2_ws/src/example/example/pose.py"
            ]

        elif node == "avoidance":

            cmd = [
                "ros2",
                "run",
                "web_control",
                "avoidance_node"
            ]

        elif node == "ai":

            cmd = [
                "ros2",
                "run",
                "web_control",
                "ai_assistant_node"
            ]

        else:

            server.robot.manual_control = True
            return jsonify({"message": "Unknown node"}), 400

        # -------------------------------------------------
        # START NODE
        # -------------------------------------------------
        server.current_process = subprocess.Popen(cmd)

        return jsonify({"message": f"{node} started"})

    except Exception as e:

        server.robot.manual_control = True
        return jsonify({"message": str(e)}), 500


# -------------------------------------------------
# STOP NODE
# -------------------------------------------------
def api_stop_node(server):

    try:

        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            server.current_process = None

        server.robot.move_x = 0.0
        server.robot.move_y = 0.0
        server.robot.rotate_dir = 0
        server.robot.cam_pan = 0.0
        server.robot.cam_tilt = 0.0

        server.robot.stop_motion_once()
        server.robot.manual_control = True

        return jsonify({"message": "Node stopped"})

    except Exception as e:

        return jsonify({"message": str(e)}), 500


# -------------------------------------------------
# MOVE
# -------------------------------------------------
def api_move(server):

    data = request.json or {}

    x = float(data.get("x", 0.0))
    y = float(data.get("y", 0.0))

    if server.robot.manual_control:
        server.robot.move_x = x
        server.robot.move_y = y

    return jsonify({"status": "ok"})


# -------------------------------------------------
# ROTATE
# -------------------------------------------------
def api_rotate(server):

    data = request.json or {}
    direction = data.get("direction", "stop")

    if direction == "cw":
        rot = -1
    elif direction == "ccw":
        rot = 1
    else:
        rot = 0

    if server.robot.manual_control:
        server.robot.rotate_dir = rot

    return jsonify({"status": "ok"})


# -------------------------------------------------
# CAMERA
# -------------------------------------------------
def api_camera(server):

    data = request.json or {}

    pan = float(data.get("pan", data.get("x", 0.0)))
    tilt = float(data.get("tilt", data.get("y", 0.0)))

    if server.robot.manual_control:
        server.robot.cam_pan = pan
        server.robot.cam_tilt = tilt

    return jsonify({"status": "ok"})
