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


def generate_frames(server):

    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 70]

    while True:

        with server.frame_lock:

            frame = None if server.frame is None else server.frame.copy()

        if frame is None:

            time.sleep(0.01)
            continue

        frame = cv2.resize(frame, (640, 480))

        ret, buffer = cv2.imencode('.jpg', frame, encode_param)

        if not ret:
            continue

        frame_bytes = buffer.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' +
               frame_bytes +
               b'\r\n')

        time.sleep(0.03)
