import signal
import subprocess
import time
from flask import request, jsonify
import os
import traceback
from openai import OpenAI
from std_msgs.msg import String

from web_control.ai_modes.core.config import llm_api_key


def register_control_routes(server):
    server.app.add_url_rule('/api/run_node', 'api_run_node', lambda: api_run_node(server), methods=['POST'])
    server.app.add_url_rule('/api/stop_node', 'api_stop_node', lambda: api_stop_node(server), methods=['POST'])
    server.app.add_url_rule('/api/move', 'api_move', lambda: api_move(server), methods=['POST'])
    server.app.add_url_rule('/api/rotate', 'api_rotate', lambda: api_rotate(server), methods=['POST'])
    server.app.add_url_rule('/api/camera', 'api_camera', lambda: api_camera(server), methods=['POST'])
    server.app.add_url_rule('/api/voice_command', 'api_voice_command', lambda: api_voice_command(server), methods=['POST'])


# -------------------------------------------------
# 🔥 FIXED PROCESS STOP (WAIT + NO DUPLICATES)
# -------------------------------------------------
def _stop_current_process(server):
    proc = getattr(server, "current_process", None)
    if not proc:
        return

    try:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGINT)

            # wait until fully dead
            for _ in range(20):
                if proc.poll() is not None:
                    break
                time.sleep(0.1)

            # force kill if still alive
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)

    except Exception:
        pass

    try:
        proc.wait(timeout=1)
    except:
        pass

    server.current_process = None


# -------------------------------------------------
# RUN NODE
# -------------------------------------------------
def api_run_node(server):
    data = request.json or {}
    node = (data.get("node") or "").strip()

    try:
        # prevent duplicate AI
        if node == "ai" and server.current_mode == "ai":
            return jsonify({"message": "AI already running"})

        # 🔥 stop previous + wait
        _stop_current_process(server)
        time.sleep(1.0)

        server.current_mode = node if node else "idle"
        server.stream_source = "raw"

        # ------------------------
        # JOYSTICK
        # ------------------------
        if node == "joystick":
            server.robot.manual_control = True
            server.stream_source = "raw"
            return jsonify({"message": "Joystick mode enabled"})

        server.robot.manual_control = False

        # ------------------------
        # BODY CONTROL
        # ------------------------
        if node == "body_control":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/body_control.py"]
            server.stream_source = "raw"

        # ------------------------
        # POSE
        # ------------------------
        elif node == "pose":
            cmd = ["python3", "/home/ubuntu/ros2_ws/src/example/example/pose.py"]
            server.stream_source = "raw"

        # ------------------------
        # AVOIDANCE
        # ------------------------
        elif node == "avoidance":
            cmd = ["python3", "-m", "web_control.autonomous.node.avoidance_node"]
            server.stream_source = "debug"

        # ------------------------
        # AI MODE
        # ------------------------
        elif node == "ai":
            cmd = ["ros2", "run", "web_control", "ai_assistant_node"]
            server.stream_source = "debug"

        # ------------------------
        # SCAN AND FIND
        # ------------------------
        elif node == "scan_and_find":
            cmd = ["python3", "-m", "web_control.autonomous.node.scan_and_find"]
            server.stream_source = "debug"

        else:
            server.current_mode = "idle"
            server.robot.manual_control = True
            return jsonify({"message": f"Unknown node: {node}"}), 400

        server.current_process = subprocess.Popen(cmd, start_new_session=True)

        print(">>> STARTING NODE:", node)

        return jsonify({"message": f"{node} started"})

    except Exception as e:
        return jsonify({"message": str(e)}), 500


# -------------------------------------------------
# STOP NODE
# -------------------------------------------------
def api_stop_node(server):
    try:
        _stop_current_process(server)

        server.current_mode = "idle"

        # 🔥 FIX STREAM FREEZE
        server.stream_source = "raw"

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
    tilt = float(data.get("tilt", data.get("y", data.get("tilt", 0.0))))

    if server.robot.manual_control and server.current_mode == "joystick":
        server.robot.cam_pan = pan
        server.robot.cam_tilt = tilt

    return jsonify({"status": "ok"})


# -------------------------------------------------
# VOICE COMMAND
# -------------------------------------------------
def api_voice_command(server):
    try:
        file = request.files.get("audio")
        if not file:
            return jsonify({"error": "No audio"}), 400

        path = "/tmp/voice.webm"
        file.save(path)

        client = OpenAI(api_key=llm_api_key)

        with open(path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en"
            )

        text = transcript.text.strip()
        print("REAL VOICE TEXT:", text)

        msg = String()
        msg.data = text
        server.voice_cmd_pub.publish(msg)

        return jsonify({"text": text})

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
