
import threading
from pkg_resources import resource_filename

__package_name__ = __name__.split('.')[0]
WWW_PATH = resource_filename(__package_name__, 'www')
API_PREFIX = '/api/v1.0'
HOST = '0.0.0.0'
PORT = 34001

default_settings = {
    "database": "pm_dashboard",
    "interval": 1,
    "spc": False,
}

db = None

def create_app():
    import flask
    from flask import request, send_from_directory
    app = flask.Flask(__name__, static_folder=WWW_PATH)

    # Host dashboard page
    @app.route('/')
    def dashboard():
        with open(f'{app.static_folder}/index.html') as f:
            return f.read()

    # Host static files for dashboard page
    @app.route('/<path:filename>')
    def serve_static(filename):
        path = app.static_folder
        if '/' in filename:
            items = filename.split('/')
            filename = items[-1]
            path = path + '/' + '/'.join(items[:-1])
        print(f'serve_static path: {path}, filename: {filename}')
        return send_from_directory(path, filename)

    # host API
    @app.route(f'{API_PREFIX}/test')
    def test():
        return {"status": True, "data": "OK"}

    def on_mqtt_connected(client, userdata, flags, rc):
        global mqtt_connected
        if rc==0:
            print("Connected to broker")
            mqtt_connected = True
        else:
            print("Connection failed")
            mqtt_connected = False

    @app.route(f'{API_PREFIX}/test-mqtt')
    def test_mqtt():
        import paho.mqtt.client as mqtt
        from socket import gaierror
        import time
        host = request.args.get("host")
        port = request.args.get("port")
        username = request.args.get("username")
        password = request.args.get("password")

        mqtt_connected = None
        client = mqtt.Client()
        client.on_connect = on_mqtt_connected
        client.username_pw_set(username, password)
        try:
            client.connect(host, port)
        except gaierror:
            return False, "Connection failed, Check hostname and port"
        timestart = time.time()
        while time.time() - timestart < 5:
            client.loop()
            if mqtt_connected == True:
                return True, None
            elif mqtt_connected == False:
                return False, "Connection failed, Check username and password"
        return False, "Timeout"

    @app.route(f'{API_PREFIX}/get-history')
    def get_history():
        try:
            num = request.args.get("n")
            num = int(num)
            data = db.get("history", n=num)
            return {"status": True, "data": data}
        except Exception as e:
            return {"status": False, "error": str(e)}
    
    return app

class PMDashboard(threading.Thread):
    def __init__(self, settings=default_settings, log=None):
        from werkzeug.serving import make_server
        from .data_logger import DataLogger
    
        threading.Thread.__init__(self)
        app = create_app()
        self.server = make_server(HOST, PORT, app)
        self.ctx = app.app_context()
        self.ctx.push()
    
        if log is None:
            import logging
            log = logging.getLogger(__name__)
        self.log = log

        self.database = None
        self.data_logger = DataLogger(settings, log=log)

        self.updata_setting(settings)

    def updata_setting(self, settings):
        from .database import Database
        global db
        if 'database' in settings:
            self.database = settings['database']
            db = Database(self.database, log=self.log)
        self.data_logger.updata_setting(settings)

    def run(self):
        self.log.info("Dashboard Server start")
        self.data_logger.start()
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

    def stop(self):
        self.data_logger.stop()
        self.shutdown()
        self.log.info("Dashboard Server stopped")

