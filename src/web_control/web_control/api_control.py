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


def _stop_current_process(server):
    proc = getattr(server, "current_process", None)
    if not proc:
        return

    try:
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=1.0)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass

    server.current_process = None


def _reset_robot_state(server):
    server.robot.move_x = 0.0
    server.robot.move_y = 0.0
    server.robot.rotate_dir = 0
    server.robot.cam_pan = 0.0
    server.robot.cam_tilt = 0.0
    server.robot.stop_motion_once()


# -------------------------------------------------
# RUN NODE
# -------------------------------------------------
def api_run_node(server):
    data = request.json or {}
    node = (data.get("node") or "").strip()

    try:
        _stop_current_process(server)
        _reset_robot_state(server)

        server.current_mode = node if node else "idle"

        # Default stream source
        server.stream_source = "raw"

        # -------------------------------------------------
        # JOYSTICK MODE (internal control only)
        # -------------------------------------------------
        if node == "joystick":
            server.robot.manual_control = True
            server.stream_source = "raw"
            return jsonify({"message": "Joystick mode enabled"})

        # -------------------------------------------------
        # OTHER MODES
        # -------------------------------------------------
        server.robot.manual_control = False

        if node == "body_control":
            cmd = [
                "python3",
                "/home/ubuntu/ros2_ws/src/example/example/body_control.py"
            ]
            server.stream_source = "raw"

        elif node == "pose":
            cmd = [
                "python3",
                "/home/ubuntu/ros2_ws/src/example/example/pose.py"
            ]
            server.stream_source = "raw"

        elif node == "avoidance":
            cmd = [
                "ros2",
                "run",
                "web_control",
                "avoidance_node"
            ]
            server.stream_source = "debug"

        elif node == "ai":
            cmd = [
                "ros2",
                "run",
                "web_control",
                "ai_assistant_node"
            ]
            server.stream_source = "raw"

        else:
            server.current_mode = "idle"
            server.robot.manual_control = True
            return jsonify({"message": f"Unknown node: {node}"}), 400

        server.current_process = subprocess.Popen(cmd)
        return jsonify({"message": f"{node} started"})

    except Exception as e:
        server.current_mode = "idle"
        server.stream_source = "raw"
        server.robot.manual_control = True
        _reset_robot_state(server)
        return jsonify({"message": str(e)}), 500


# -------------------------------------------------
# STOP NODE
# -------------------------------------------------
def api_stop_node(server):
    try:
        _stop_current_process(server)

        server.current_mode = "idle"
        server.stream_source = "raw"
        server.robot.manual_control = True

        _reset_robot_state(server)

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

    if server.robot.manual_control and server.current_mode == "joystick":
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

    if server.robot.manual_control and server.current_mode == "joystick":
        server.robot.rotate_dir = rot

    return jsonify({"status": "ok"})


# -------------------------------------------------
# CAMERA
# -------------------------------------------------
def api_camera(server):
    data = request.json or {}

    pan = float(data.get("pan", data.get("x", 0.0)))
    tilt = float(data.get("tilt", data.get("y", 0.0)))

    if server.robot.manual_control and server.current_mode == "joystick":
        server.robot.cam_pan = pan
        server.robot.cam_tilt = tilt

    return jsonify({"status": "ok"})
