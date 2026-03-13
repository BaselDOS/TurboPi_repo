import threading

from flask import Flask, render_template
from flask_socketio import SocketIO

from .api_control import register_control_routes
from .api_status import register_status_routes
from .api_stream import register_stream_routes


class WebServer:

    def __init__(self, node, pkg_share):
        self.node = node
        self.robot = node.robot

        self.battery_voltage = None
        self.camera_ok = False
        self.frame = None
        self.frame_lock = threading.Lock()

        self.current_process = None

        self.app = Flask(
            __name__,
            template_folder=pkg_share + '/templates',
            static_folder=pkg_share + '/static'
        )

        self.socketio = SocketIO(self.app, cors_allowed_origins="*")

        # Page routes
        self.app.add_url_rule('/', 'index', self.index)
        self.app.add_url_rule('/run', 'run', self.run_page)

        # API routes
        register_status_routes(self)
        register_control_routes(self)
        register_stream_routes(self)

        # Start server thread
        t = threading.Thread(target=self._run_server, daemon=True)
        t.start()

    def index(self):
        return render_template('index.html')

    def run_page(self):
        return render_template('run.html')

    def _run_server(self):
        self.socketio.run(
            self.app,
            host='0.0.0.0',
            port=5000,
            allow_unsafe_werkzeug=True
        )
