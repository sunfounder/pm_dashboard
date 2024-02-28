
import threading
import logging

import flask
from flask import request, send_from_directory
from flask_cors import CORS, cross_origin
from pkg_resources import resource_filename
from werkzeug.serving import make_server

from .data_logger import DataLogger
from .database import Database

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

__db__ = None
__config__ = {}
__app__ = flask.Flask(__name__, static_folder=WWW_PATH)
cors = CORS(__app__)
__app__.config['CORS_HEADERS'] = 'Content-Type'
__device_info__ = {}

__on_config_changed__ = lambda config: None

# Host dashboard page
@__app__.route('/')
@cross_origin()
def dashboard():
    with open(f'{__app__.static_folder}/index.html') as f:
        return f.read()

# Host static files for dashboard page
@__app__.route('/<path:filename>')
@cross_origin()
def serve_static(filename):
    path = __app__.static_folder
    if '/' in filename:
        items = filename.split('/')
        filename = items[-1]
        path = path + '/' + '/'.join(items[:-1])
    print(f'serve_static path: {path}, filename: {filename}')
    return send_from_directory(path, filename)

def on_mqtt_connected(client, userdata, flags, rc):
    global mqtt_connected
    if rc==0:
        print("Connected to broker")
        mqtt_connected = True
    else:
        print("Connection failed")
        mqtt_connected = False

# host API

@__app__.route(f'{API_PREFIX}/get-device-info')
@cross_origin()
def get_device_info():
    return {"status": True, "data": __device_info__}

@__app__.route(f'{API_PREFIX}/test')
@cross_origin()
def test():
    return {"status": True, "data": "OK"}

@__app__.route(f'{API_PREFIX}/test-mqtt')
@cross_origin()
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

@__app__.route(f'{API_PREFIX}/get-history')
@cross_origin()
def get_history():
    try:
        num = request.args.get("n")
        num = int(num)
        data = __db__.get("history", n=num)
        return {"status": True, "data": data}
    except Exception as e:
        return {"status": False, "error": str(e)}

@__app__.route(f'{API_PREFIX}/get-time-range')
@cross_origin()
def get_time_range():
    try:
        start = request.args.get("start")
        end = request.args.get("end")
        key = request.args.get("key")
        data = __db__.get_data_by_time_range("history", start, end, key)
        return {"status": True, "data": data}
    except Exception as e:
        return {"status": False, "error": str(e)}

@__app__.route(f'{API_PREFIX}/get-config')
@cross_origin()
def get_config():
    return {"status": True, "data": __config__}

@__app__.route(f'{API_PREFIX}/set-config', methods=['POST'])
@cross_origin()
def set_config():
    data = request.json['data']
    print("set_config: ", data)
    __on_config_changed__(data)
    return {"status": True, "data": __config__}


class PMDashboard(threading.Thread):
    def __init__(self, device_info=None, peripherals=[], settings=default_settings, config=None, get_logger=None):
        global __config__, __device_info__, __db__
        __device_info__ = device_info

        threading.Thread.__init__(self)
        self.server = make_server(HOST, PORT, __app__)
        self.ctx = __app__.app_context()
        self.ctx.push()
    
        if get_logger is None:
            get_logger = logging.getLogger
        self.log = get_logger(__name__)

        self.data_logger = DataLogger(settings=settings, peripherals=peripherals, get_logger=get_logger)
        __db__ = Database(settings['database'], get_logger=get_logger)
        for key, value in config.items():
            __config__[key] = value

    def set_on_config_changed(self, func):
        global __on_config_changed__
        __on_config_changed__ = func

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

