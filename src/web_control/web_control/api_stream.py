import time
import cv2
from flask import Response


def register_stream_routes(server):
    server.app.add_url_rule('/stream', 'stream', lambda: stream(server))


def stream(server):
    return Response(
        generate_frames(server),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


def _get_active_frame(server):
    with server.frame_lock:
        if server.stream_source == "debug" and server.debug_frame is not None:
            return server.debug_frame.copy()

        if server.raw_frame is not None:
            return server.raw_frame.copy()

        return None


def generate_frames(server):
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]

    while True:
        frame = _get_active_frame(server)

        if frame is None:
            time.sleep(0.03)
            continue

        frame = cv2.resize(frame, (640, 480))

        ret, buffer = cv2.imencode('.jpg', frame, encode_param)
        if not ret:
            time.sleep(0.03)
            continue

        frame_bytes = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            frame_bytes +
            b'\r\n'
        )

        time.sleep(0.03)
