import subprocess
import time
from flask import request, jsonify


# -------------------------------------------------
# Register API routes
# -------------------------------------------------
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
# Wait for ROS service
# -------------------------------------------------
def wait_for_service(service_name, timeout=10):

    start = time.time()

    while time.time() - start < timeout:

        result = subprocess.run(
            ["ros2", "service", "list"],
            capture_output=True,
            text=True
        )

        if service_name in result.stdout:
            return True

        time.sleep(0.5)

    return False


# -------------------------------------------------
# Run node
# -------------------------------------------------
def api_run_node(server):

    data = request.json or {}
    node = data.get("node")

    try:

        # stop previous node
        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            server.current_process = None
            time.sleep(0.5)

        # reset robot movement
        server.robot.move_x = 0.0
        server.robot.move_y = 0.0
        server.robot.rotate_dir = 0

        # joystick mode
        if node == "joystick":

            server.robot.manual_control = True
            return jsonify({"message": "Joystick mode enabled"})

        server.robot.manual_control = False

        # select node
        if node == "body_control":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/body_control.py"]

        elif node == "pose":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/pose.py"]

        elif node == "avoidance":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/avoidance_node.py"]

        else:
            server.robot.manual_control = True
            return jsonify({"message": "Unknown node"}), 400


        # launch node
        server.current_process = subprocess.Popen(cmd)

        # activate avoidance
        if node == "avoidance":

            if wait_for_service("/avoidance_node/enter"):

                subprocess.Popen([
                    "ros2", "service", "call",
                    "/avoidance_node/enter",
                    "std_srvs/srv/Trigger"
                ])

                time.sleep(0.5)

                subprocess.Popen([
                    "ros2", "service", "call",
                    "/avoidance_node/set_running",
                    "std_srvs/srv/SetBool",
                    "{data: true}"
                ])

        return jsonify({"message": f"{node} started"})


    except Exception as e:

        server.robot.manual_control = True
        return jsonify({"message": str(e)}), 500


# -------------------------------------------------
# Stop node
# -------------------------------------------------
def api_stop_node(server):

    try:

        # stop avoidance
        try:
            subprocess.Popen([
                "ros2", "service", "call",
                "/avoidance_node/set_running",
                "std_srvs/srv/SetBool",
                "{data: false}"
            ])
        except:
            pass

        # kill running process
        if hasattr(server, "current_process") and server.current_process:
            server.current_process.kill()
            server.current_process = None

        server.robot.manual_control = True

        # reset robot movement
        server.robot.move_x = 0.0
        server.robot.move_y = 0.0
        server.robot.rotate_dir = 0

        # reset camera
        server.robot.cam_pan = 0.0
        server.robot.cam_tilt = 0.0

        return jsonify({"message": "Node stopped"})

    except Exception as e:

        return jsonify({"message": str(e)}), 500


# -------------------------------------------------
# Move joystick
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
# Rotate buttons
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
# Camera joystick
# -------------------------------------------------
def api_camera(server):

    data = request.json or {}

    pan = float(data.get("pan", data.get("x", 0.0)))
    tilt = float(data.get("tilt", data.get("y", 0.0)))

    server.robot.cam_pan = pan
    server.robot.cam_tilt = tilt

    return jsonify({"status": "ok"})
